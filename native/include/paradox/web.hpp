// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "store.hpp"
#include <functional>
#include <memory>
namespace paradox {
class Web {
  public:
    Web(std::string host, int port, std::string token);
    ~Web();
    void publish(Json snapshot);
    std::vector<std::string> commands();
    void post(std::string url, Json body, std::string api_key = {});
    void request(std::string tag, std::string url, std::string api_key, Json body = nullptr);
    std::vector<std::pair<std::string, Json>> responses();
    std::string error() const;

  private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
std::string random_token();
std::string sha256(std::string_view);
bool constant_equal(std::string_view, std::string_view);
} // namespace paradox
