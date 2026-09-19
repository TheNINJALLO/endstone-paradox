// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <condition_variable>
#include <filesystem>
#include <mutex>
#include <nlohmann/json.hpp>
#include <thread>
#include <unordered_map>
struct sqlite3;
namespace paradox {
using Json = nlohmann::json;
// SQLite stays on a worker after startup. Event handlers only touch the cache.
class Store {
  public:
    explicit Store(const std::filesystem::path &);
    ~Store();
    Store(const Store &) = delete;
    Json get(const std::string &table, const std::string &key, Json fallback = nullptr) const;
    Json all(const std::string &table) const;
    void set(const std::string &table, const std::string &key, Json value);
    void erase(const std::string &table, const std::string &key);
    void flush();
    std::string error() const;

  private:
    sqlite3 *db_{};
    mutable std::mutex mutex_;
    std::condition_variable wake_, drained_;
    std::unordered_map<std::string, Json> tables_;
    struct Write {
        std::string table, key;
        Json value;
        bool remove{};
    };
    std::unordered_map<std::string, Write> pending_;
    std::jthread worker_;
    bool busy_{}, stopping_{};
    std::string error_;
    void run();
    void sql(const std::string &);
    void backup(const std::filesystem::path &);
};
} // namespace paradox
