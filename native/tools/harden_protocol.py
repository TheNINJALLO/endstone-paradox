"""Apply bounded inspection to the exact protocol compiler pinned in references.lock.json.

Budgets are local inspection limits, not assertions that a player is cheating.
The adapter fails open on budget/schema errors and leaves validation to BDS.
"""

from pathlib import Path
import sys

root = Path(sys.argv[1])


def patch(path, old, new, count=1):
    p = root / path
    text = p.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != count:
        raise SystemExit(f"Protocol source changed: {path}; review the patch")
    p.write_text(text.replace(old, new), encoding="utf-8")


patch(
    "include/bedrock/protocol/stream.hpp",
    "#include <system_error>",
    "#include <system_error>\n#include <stdexcept>",
)
patch(
    "include/bedrock/protocol/stream.hpp",
    "    explicit BinaryReader(std::string_view buf) : view_(buf) {}",
    """    explicit BinaryReader(std::string_view buf) : view_(buf) {}
    void inspectElements(std::uint64_t count) {
        if (count > inspection_budget_) throw std::length_error("protocol inspection budget");
        inspection_budget_ -= static_cast<std::size_t>(count);
    }
    struct InspectionScope {
        BinaryReader &reader;
        explicit InspectionScope(BinaryReader &r) : reader(r) {
            if (++reader.inspection_depth_ > 64) throw std::length_error("protocol inspection depth");
            reader.inspectElements(1);
        }
        ~InspectionScope() { --reader.inspection_depth_; }
    };
private:
    std::size_t inspection_budget_{8192}, inspection_depth_{};
public:""",
)
patch(
    "include/bedrock/protocol/stream.hpp",
    "        std::string out(*len, '\\0');",
    """        if (*len > getUnreadLength()) return std::unexpected(std::make_error_code(std::errc::message_size));
        std::string out(*len, '\\0');""",
)
patch(
    "src/bedrock_protocol/compiler/cpp/field.py",
    'p.print(f"if (!len{depth}) return std::unexpected(len{depth}.error());\\n")',
    'p.print(f"if (!len{depth}) return std::unexpected(len{depth}.error());\\n")\n        p.print(f"stream.inspectElements(static_cast<std::uint64_t>(*len{depth}));\\n")',
    count=2,
)
patch(
    "include/bedrock/protocol/nbt.hpp",
    "inline std::expected<Tag, std::error_code> readTag(BinaryReader &stream, Type type)\n{",
    "inline std::expected<Tag, std::error_code> readTag(BinaryReader &stream, Type type)\n{\n    BinaryReader::InspectionScope inspection(stream);",
)
patch(
    "include/bedrock/protocol/data_store.hpp",
    "    static auto deserialize(BinaryReader &stream) -> std::expected<DynamicValue, std::error_code>\n    {",
    "    static auto deserialize(BinaryReader &stream) -> std::expected<DynamicValue, std::error_code>\n    {\n        BinaryReader::InspectionScope inspection(stream);",
)
