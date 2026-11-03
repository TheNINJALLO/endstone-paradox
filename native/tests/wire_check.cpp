// SPDX-License-Identifier: GPL-3.0-or-later
#include "paradox/protocol.hpp"
#include <fstream>
#include <iostream>
#include <map>
#include <nlohmann/json.hpp>
#include <stdexcept>

int main(int argc, char **argv) {
    try {
        if (argc != 2)
            throw std::runtime_error("Usage: paradox_wire_check captured-payloads.json");
        std::ifstream file(argv[1]);
        auto fixtures = nlohmann::json::parse(file);
        std::map<int, unsigned> counts;
        for (const auto &fixture : fixtures) {
            const int id = fixture.at("id");
            const auto hex = fixture.at("payload").get<std::string>();
            if (hex.size() % 2 || hex.size() > 524288)
                throw std::runtime_error("Invalid captured payload size");
            std::string bytes;
            auto digit = [](char c) -> unsigned {
                if (c >= '0' && c <= '9') return c - '0';
                if (c >= 'a' && c <= 'f') return c - 'a' + 10;
                throw std::runtime_error("Invalid payload hex digit");
            };
            for (std::size_t i = 0; i < hex.size(); i += 2)
                bytes.push_back(static_cast<char>((digit(hex[i]) << 4) | digit(hex[i + 1])));
            auto result = paradox::inspect_packet(id, bytes, fixture.at("outgoing"));
            if (!result.decoded || result.malformed)
                throw std::runtime_error("Native wire packet " + std::to_string(id) + " failed: " + result.reason);
            ++counts[id];
        }
        if (counts[144] < 20 || counts[28] < 1)
            throw std::runtime_error("Need actual player input and effect payloads");
        std::cout << "All " << fixtures.size() << " native protocol-2225 payloads decoded without malformed flags\n";
        for (const auto &[id, count] : counts)
            std::cout << id << ": " << count << '\n';
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
