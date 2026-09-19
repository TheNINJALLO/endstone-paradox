// SPDX-License-Identifier: GPL-3.0-or-later
#include "paradox/web.hpp"
#include <deque>
#include <httplib.h>
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/rand.h>

namespace paradox {
std::string hex(const unsigned char *bytes, std::size_t n) {
    static constexpr char chars[] = "0123456789abcdef";
    std::string out;
    out.reserve(n * 2);
    for (std::size_t i = 0; i < n; ++i) {
        out += chars[bytes[i] >> 4];
        out += chars[bytes[i] & 15];
    }
    return out;
}
std::string random_token() {
    unsigned char data[32];
    if (RAND_bytes(data, sizeof(data)) != 1)
        throw std::runtime_error("Secure token generation failed");
    return hex(data, sizeof(data));
}
std::string sha256(std::string_view text) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned length{};
    if (EVP_Digest(text.data(), text.size(), digest, &length, EVP_sha256(), nullptr) != 1)
        throw std::runtime_error("Hash failed");
    return hex(digest, length);
}
bool constant_equal(std::string_view a, std::string_view b) {
    return a.size() == b.size() && CRYPTO_memcmp(a.data(), b.data(), a.size()) == 0;
}
static constexpr auto dashboard =
    R"html(<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Paradox</title><style>body{font:16px system-ui;background:#10191e;color:#dfe8eb;max-width:1100px;margin:40px auto;padding:20px}input,button{padding:10px;margin:4px;background:#22343c;color:white;border:1px solid #68818b;border-radius:5px}button{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1b2a31;padding:15px}table{width:100%;border-collapse:collapse}td,th{padding:9px;text-align:left;border-bottom:1px solid #3a505a}.muted{color:#b4c9d0}h1{color:#82ddbe}</style><h1>Paradox</h1><p class="muted">Server protection and moderation</p><section id="login"><label>Access token <input id="token" type="password" autocomplete="off"></label><button id="connect">Connect</button></section><p id="status" role="status"></p><section id="panel" hidden><h2>Players</h2><table><thead><tr><th>Name</th><th>Ping</th><th>Detection</th></tr></thead><tbody id="players"></tbody></table><h2>Modules</h2><div id="modules"></div><h2>Moderation command</h2><input id="command" placeholder="ac-modules" size="50"><button id="send">Run</button><h2>Recent evidence</h2><pre id="evidence"></pre></section><script src="/app.js"></script></html>)html";
static constexpr auto script =
    R"js(let token='';const $=id=>document.getElementById(id);async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error('Request failed: '+r.status);return r.json()}async function refresh(){try{const s=await api('/api/status');$('panel').hidden=false;$('login').hidden=true;$('status').textContent=s.version+' | '+s.tps.toFixed(1)+' TPS';$('players').replaceChildren();for(const p of s.players){const tr=document.createElement('tr');for(const v of [p.name,p.ping+' ms',p.ready?'Active':p.reason]){const td=document.createElement('td');td.textContent=v;tr.append(td)}$('players').append(tr)}$('modules').replaceChildren();for(const [name,m] of Object.entries(s.modules)){const b=document.createElement('button');b.textContent=name+': '+(m.enabled?'on':'off');b.onclick=async()=>{await api('/api/command',{command:'ac-modstate '+name+' '+(m.enabled?'off':'on')});setTimeout(refresh,300)};$('modules').append(b)}$('evidence').textContent=JSON.stringify(s.evidence,null,2)}catch(e){$('status').textContent=e.message}}$('connect').onclick=()=>{token=$('token').value;$('token').value='';refresh()};$('send').onclick=async()=>{try{await api('/api/command',{command:$('command').value});$('status').textContent='Command queued; results appear in the server console.'}catch(e){$('status').textContent=e.message}};setInterval(()=>{if(token)refresh()},5000);)js";
struct Web::Impl {
    httplib::Server server;
    std::jthread listener, sender;
    mutable std::mutex mutex;
    std::condition_variable wake;
    Json snapshot = Json::object();
    std::deque<std::string> commands;
    struct Post {
        std::string url, key;
        Json body;
        std::string tag;
        bool get{};
    };
    std::deque<Post> posts;
    std::vector<std::pair<std::string, Json>> responses;
    std::string token, error;
    bool stopping{};
    bool auth(const httplib::Request &r, httplib::Response &s) {
        const auto header = r.get_header_value("Authorization");
        if (!constant_equal(header, "Bearer " + token)) {
            s.status = 401;
            s.set_content("{\"error\":\"unauthorized\"}", "application/json");
            return false;
        }
        return true;
    }
};
Web::Web(std::string host, int port, std::string token) : impl_(std::make_unique<Impl>()) {
    auto &i = *impl_;
    i.token = std::move(token);
    i.server.set_payload_max_length(8192);
    i.server.set_read_timeout(3);
    i.server.set_write_timeout(3);
    i.server.set_keep_alive_max_count(10);
    i.server.set_default_headers(
        {{"Cache-Control", "no-store"},
         {"X-Content-Type-Options", "nosniff"},
         {"Content-Security-Policy",
          "default-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'"}});
    i.server.Get("/", [](const auto &, auto &r) { r.set_content(dashboard, "text/html; charset=utf-8"); });
    i.server.Get("/app.js", [](const auto &, auto &r) { r.set_content(script, "text/javascript; charset=utf-8"); });
    i.server.Get("/api/status", [&i](const auto &r, auto &s) {
        if (!i.auth(r, s))
            return;
        std::lock_guard lock(i.mutex);
        s.set_content(i.snapshot.dump(), "application/json");
    });
    i.server.Post("/api/command", [&i](const auto &r, auto &s) {
        if (!i.auth(r, s))
            return;
        auto data = Json::parse(r.body, nullptr, false);
        if (!data.is_object() || !data.contains("command") || !data["command"].is_string()) {
            s.status = 400;
            return;
        }
        auto command = data["command"].template get<std::string>();
        if (!command.starts_with("ac-") || command.size() > 1024 ||
            command.find_first_of("\r\n\0", 0, 3) != std::string::npos) {
            s.status = 400;
            return;
        }
        std::lock_guard lock(i.mutex);
        if (i.commands.size() >= 32) {
            s.status = 429;
            return;
        }
        i.commands.push_back(command);
        s.status = 202;
        s.set_content("{\"queued\":true}", "application/json");
    });
    // Bind before starting the worker so startup reports address conflicts accurately.
    if (port > 0 && !i.server.bind_to_port(host, port))
        throw std::runtime_error("Web interface could not bind configured address");
    if (port > 0)
        i.listener = std::jthread([&i] { i.server.listen_after_bind(); });
    i.sender = std::jthread([&i] {
        for (;;) {
            Impl::Post p;
            {
                std::unique_lock lock(i.mutex);
                i.wake.wait(lock, [&] { return i.stopping || !i.posts.empty(); });
                if (i.stopping)
                    return;
                p = std::move(i.posts.front());
                i.posts.pop_front();
            }
            try {
                if (!p.url.starts_with("https://"))
                    throw std::runtime_error("Integrations require HTTPS");
                auto slash = p.url.find('/', 8);
                std::string origin = p.url.substr(0, slash),
                            path = slash == std::string::npos ? "/" : p.url.substr(slash);
                httplib::Client client(origin);
                client.set_connection_timeout(3);
                client.set_read_timeout(5);
                client.set_write_timeout(5);
                httplib::Headers headers;
                if (!p.key.empty())
                    headers.emplace("X-API-Key", p.key);
                std::string response_body;
                httplib::Request request;
                request.method = p.get ? "GET" : "POST";
                request.path = path;
                request.headers = headers;
                if (!p.get) {
                    request.body = p.body.dump();
                    request.headers.emplace("Content-Type", "application/json");
                }
                request.content_receiver = [&response_body](const char *data, std::size_t length, std::uint64_t,
                                                            std::uint64_t) {
                    if (length > 4194304 - response_body.size())
                        return false;
                    response_body.append(data, length);
                    return true;
                };
                client.set_max_timeout(std::chrono::milliseconds(10000));
                auto response = client.send(request);
                if (!response || response->status < 200 || response->status >= 300)
                    throw std::runtime_error("Integration request failed");
                if (!p.tag.empty()) {
                    if (response_body.size() > 4194304)
                        throw std::runtime_error("Integration response exceeds inspection limit");
                    auto data = Json::parse(response_body, nullptr, false);
                    if (data.is_discarded())
                        throw std::runtime_error("Invalid integration response");
                    std::lock_guard lock(i.mutex);
                    if (i.responses.size() < 16)
                        i.responses.emplace_back(p.tag, std::move(data));
                }
            } catch (const std::exception &e) {
                std::lock_guard lock(i.mutex);
                i.error = e.what();
            }
        }
    });
}
Web::~Web() {
    if (!impl_)
        return;
    auto &i = *impl_;
    i.server.stop();
    {
        std::lock_guard lock(i.mutex);
        i.stopping = true;
    }
    i.wake.notify_all();
    if (i.listener.joinable())
        i.listener.join();
    if (i.sender.joinable())
        i.sender.join();
}
void Web::publish(Json snapshot) {
    std::lock_guard lock(impl_->mutex);
    impl_->snapshot = std::move(snapshot);
}
std::vector<std::string> Web::commands() {
    std::lock_guard lock(impl_->mutex);
    std::vector<std::string> out(impl_->commands.begin(), impl_->commands.end());
    impl_->commands.clear();
    return out;
}
void Web::post(std::string url, Json body, std::string key) {
    std::lock_guard lock(impl_->mutex);
    if (impl_->posts.size() < 128)
        impl_->posts.push_back({std::move(url), std::move(key), std::move(body)});
    impl_->wake.notify_one();
}
void Web::request(std::string tag, std::string url, std::string key, Json body) {
    std::lock_guard lock(impl_->mutex);
    if (impl_->posts.size() < 128) {
        bool get = body.is_null();
        impl_->posts.push_back({std::move(url), std::move(key), std::move(body), std::move(tag), get});
    }
    impl_->wake.notify_one();
}
std::vector<std::pair<std::string, Json>> Web::responses() {
    std::lock_guard lock(impl_->mutex);
    std::vector<std::pair<std::string, Json>> out;
    out.swap(impl_->responses);
    return out;
}
std::string Web::error() const {
    std::lock_guard lock(impl_->mutex);
    return impl_->error;
}
} // namespace paradox
