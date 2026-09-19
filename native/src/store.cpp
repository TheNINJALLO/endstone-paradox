// SPDX-License-Identifier: GPL-3.0-or-later
#include "paradox/store.hpp"
#include <cctype>
#include <sqlite3.h>
#include <stdexcept>

namespace paradox {
namespace {
std::string identifier(const std::string &name) {
    if (name.empty() || name.size() > 64)
        throw std::invalid_argument("Invalid table name");
    for (unsigned char c : name)
        if (!std::isalnum(c) && c != '_')
            throw std::invalid_argument("Invalid table name");
    return "\"" + name + "\"";
}
struct Statement {
    sqlite3_stmt *p{};
    Statement(sqlite3 *db, const std::string &query) {
        if (sqlite3_prepare_v2(db, query.c_str(), -1, &p, nullptr) != SQLITE_OK)
            throw std::runtime_error(sqlite3_errmsg(db));
    }
    ~Statement() {
        sqlite3_finalize(p);
    }
    void bind(int index, const std::string &s) {
        if (sqlite3_bind_text(p, index, s.data(), static_cast<int>(s.size()), SQLITE_TRANSIENT) != SQLITE_OK)
            throw std::runtime_error("SQLite bind failed");
    }
    void write(sqlite3 *db) {
        if (sqlite3_step(p) != SQLITE_DONE)
            throw std::runtime_error(sqlite3_errmsg(db));
    }
};
} // namespace
void Store::sql(const std::string &query) {
    if (sqlite3_exec(db_, query.c_str(), nullptr, nullptr, nullptr) != SQLITE_OK)
        throw std::runtime_error(sqlite3_errmsg(db_));
}
void Store::backup(const std::filesystem::path &path) {
    const auto temporary = path.string() + ".tmp";
    sqlite3 *copy{};
    if (sqlite3_open(temporary.c_str(), &copy) != SQLITE_OK) {
        if (copy)
            sqlite3_close(copy);
        throw std::runtime_error("Cannot open migration backup");
    }
    auto *backup = sqlite3_backup_init(copy, "main", db_, "main");
    const int result = backup ? sqlite3_backup_step(backup, -1) : SQLITE_ERROR;
    if (backup)
        sqlite3_backup_finish(backup);
    sqlite3_close(copy);
    if (result != SQLITE_DONE) {
        std::filesystem::remove(temporary);
        throw std::runtime_error("Cannot create consistent migration backup");
    }
    std::filesystem::rename(temporary, path);
}
Store::Store(const std::filesystem::path &path) {
    std::filesystem::create_directories(path.parent_path());
    const bool existing = std::filesystem::exists(path);
    if (sqlite3_open_v2(path.string().c_str(), &db_, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX,
                        nullptr) != SQLITE_OK) {
        std::string reason = db_ ? sqlite3_errmsg(db_) : "SQLite allocation failed";
        if (db_)
            sqlite3_close(db_);
        db_ = nullptr;
        throw std::runtime_error(reason);
    }
    try {
        sqlite3_busy_timeout(db_, 5000);
        if (existing && !std::filesystem::exists(path.string() + ".pre-native.bak"))
            backup(path.string() + ".pre-native.bak");
        sql("PRAGMA journal_mode=WAL");
        sql("PRAGMA synchronous=FULL");
        Statement tables(db_, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'");
        while (sqlite3_step(tables.p) == SQLITE_ROW) {
            std::string name = reinterpret_cast<const char *>(sqlite3_column_text(tables.p, 0));
            if (name == "_meta")
                continue;
            Statement rows(db_, "SELECT key,value FROM " + identifier(name));
            auto &cache = tables_[name];
            cache = Json::object();
            int result;
            while ((result = sqlite3_step(rows.p)) == SQLITE_ROW) {
                auto *key = sqlite3_column_text(rows.p, 0), *value = sqlite3_column_text(rows.p, 1);
                if (!key || !value)
                    throw std::runtime_error("Null key/value in existing database");
                cache[reinterpret_cast<const char *>(key)] = Json::parse(reinterpret_cast<const char *>(value));
            }
            if (result != SQLITE_DONE)
                throw std::runtime_error(sqlite3_errmsg(db_));
        }
        worker_ = std::jthread([this] { run(); });
    } catch (...) {
        sqlite3_close(db_);
        db_ = nullptr;
        throw;
    }
}
Store::~Store() {
    {
        std::lock_guard lock(mutex_);
        stopping_ = true;
    }
    wake_.notify_one();
    if (worker_.joinable())
        worker_.join();
    if (db_)
        sqlite3_close(db_);
}
Json Store::get(const std::string &table, const std::string &key, Json fallback) const {
    std::lock_guard lock(mutex_);
    auto t = tables_.find(table);
    if (t == tables_.end())
        return fallback;
    auto v = t->second.find(key);
    return v == t->second.end() ? fallback : *v;
}
Json Store::all(const std::string &table) const {
    std::lock_guard lock(mutex_);
    auto i = tables_.find(table);
    return i == tables_.end() ? Json::object() : i->second;
}
void Store::set(const std::string &table, const std::string &key, Json value) {
    identifier(table);
    {
        std::lock_guard lock(mutex_);
        if (!error_.empty())
            throw std::runtime_error(error_);
        if (stopping_ || pending_.size() >= 8192)
            throw std::runtime_error("Persistence queue unavailable");
        auto &t = tables_[table];
        if (t.is_null())
            t = Json::object();
        t[key] = value;
        pending_[table + "\n" + key] = {table, key, std::move(value), false};
    }
    wake_.notify_one();
}
void Store::erase(const std::string &table, const std::string &key) {
    identifier(table);
    {
        std::lock_guard lock(mutex_);
        if (!error_.empty())
            throw std::runtime_error(error_);
        if (stopping_ || pending_.size() >= 8192)
            throw std::runtime_error("Persistence queue unavailable");
        auto i = tables_.find(table);
        if (i != tables_.end())
            i->second.erase(key);
        pending_[table + "\n" + key] = {table, key, nullptr, true};
    }
    wake_.notify_one();
}
void Store::flush() {
    std::unique_lock lock(mutex_);
    wake_.notify_one();
    drained_.wait(lock, [&] { return (!busy_ && pending_.empty()) || !error_.empty(); });
    if (!error_.empty())
        throw std::runtime_error(error_);
}
std::string Store::error() const {
    std::lock_guard lock(mutex_);
    return error_;
}
void Store::run() {
    for (;;) {
        std::unordered_map<std::string, Write> writes;
        {
            std::unique_lock lock(mutex_);
            wake_.wait(lock, [&] { return stopping_ || !pending_.empty(); });
            if (pending_.empty() && stopping_)
                break;
            writes.swap(pending_);
            busy_ = true;
        }
        try {
            sql("BEGIN IMMEDIATE");
            for (const auto &[_, w] : writes) {
                auto table = identifier(w.table);
                sql("CREATE TABLE IF NOT EXISTS " + table +
                    " (key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at REAL DEFAULT (julianday('now')))");
                if (w.remove) {
                    Statement q(db_, "DELETE FROM " + table + " WHERE key=?");
                    q.bind(1, w.key);
                    q.write(db_);
                } else {
                    Statement q(db_, "INSERT INTO " + table +
                                         " (key,value,updated_at) VALUES (?,?,julianday('now')) ON CONFLICT(key) DO "
                                         "UPDATE SET value=excluded.value,updated_at=excluded.updated_at");
                    q.bind(1, w.key);
                    q.bind(2, w.value.dump());
                    q.write(db_);
                }
            }
            sql("COMMIT");
        } catch (const std::exception &e) {
            sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
            std::lock_guard lock(mutex_);
            error_ = e.what();
            busy_ = false;
            drained_.notify_all();
            return;
        }
        {
            std::lock_guard lock(mutex_);
            busy_ = false;
        }
        drained_.notify_all();
    }
}
} // namespace paradox
