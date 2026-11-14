"""Generate an isolated AUTOSAR-style project with 5,125 C/H files by default."""

import argparse
import json
from pathlib import Path


def generate_project(output: Path, *, components: int = 64, stages: int = 40) -> Path:
    """Create deterministic synthetic sources in a new directory, never overwrite sources.

    Each component has its own call chain, RTE channel, global stimulus and publisher.
    The bounded size options also allow small, fast regression fixtures.
    """
    if (type(components) is not int or not 1 <= components <= 96
            or type(stages) is not int or not 2 <= stages <= 48):
        raise ValueError("components must be 1..96 and stages must be 2..48 integers")
    output.mkdir(parents=True, exist_ok=False)

    def write(relative: str, source: str) -> None:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="ascii", newline="\n") as stream:
            stream.write(source)

    write("include/Mega_Types.h", """/* Synthetic types; not an AUTOSAR stack. */
#ifndef MEGA_TYPES_H
#define MEGA_TYPES_H
#include <stdint.h>
typedef uint8_t uint8;
typedef uint16_t uint16;
typedef uint8 Std_ReturnType;
typedef struct { uint16 raw; uint8 quality; uint8 enabled; } Mega_Stimulus;
#define RTE_E_OK ((Std_ReturnType)0u)
#endif
""")
    declarations = []
    memory = ['#include "Rte_Mega.h"\n']
    for component in range(components):
        name = f"Mega_{component:03}"
        channel = f"Mega{component:03}_Pedal"
        declarations.append(f"""extern Mega_Stimulus g_Stimulus_{component:03};
extern uint8 g_ReadFailure_{component:03};
Std_ReturnType Rte_Read_{channel}(uint16 *value);
Std_ReturnType Rte_Write_{channel}(uint16 value);
""")
        memory.append(f"""Mega_Stimulus g_Stimulus_{component:03} = {{0u, 0u, 0u}};
uint8 g_ReadFailure_{component:03} = 0u;
static uint16 buffer_{component:03} = 0u;
Std_ReturnType Rte_Read_{channel}(uint16 *value)
{{
    if (g_ReadFailure_{component:03} != 0u) {{ return 1u; }}
    *value = buffer_{component:03};
    return RTE_E_OK;
}}
Std_ReturnType Rte_Write_{channel}(uint16 value)
{{
    buffer_{component:03} = value;
    return RTE_E_OK;
}}
""")
        for stage in range(stages):
            symbol = f"{name}_Stage_{stage:02}"
            header = f"#ifndef {symbol.upper()}_H\n#define {symbol.upper()}_H\n#include \"Mega_Types.h\"\nuint16 {symbol}(void);\n"
            if stage == stages - 1:
                header += f"void {name}_Publish(void);\n"
                body = f"""#include "Stage_{stage:02}.h"
#include "Rte_Mega.h"
uint16 {symbol}(void)
{{
    uint16 pedal = 0u;
    if (Rte_Read_{channel}(&pedal) != RTE_E_OK) {{ return 0u; }}
    return pedal;
}}
/* Separate runnable: consumers never call the publisher. */
void {name}_Publish(void)
{{
    uint16 converted = 0u;
    if (g_Stimulus_{component:03}.enabled != 0u) {{
        if (g_Stimulus_{component:03}.quality == 1u) {{
            converted = (uint16)(g_Stimulus_{component:03}.raw * 2u);
        }} else if (g_Stimulus_{component:03}.quality == 2u) {{
            converted = (uint16)(g_Stimulus_{component:03}.raw + 10u);
        }} else {{
            converted = 0u;
        }}
        (void)Rte_Write_{channel}(converted);
    }}
    /* Disabled: the prior RTE memory is retained. */
}}
"""
            else:
                body = f"""#include "Stage_{stage:02}.h"
#include "Stage_{stage + 1:02}.h"
uint16 {symbol}(void)
{{
    uint16 value = {name}_Stage_{stage + 1:02}();
    if (value > 100u) {{
        return 100u;
    }} else if (value > 0u) {{
        return value;
    }} else {{
        return 0u;
    }}
}}
"""
            directory = f"components/{name}"
            write(f"{directory}/Stage_{stage:02}.h", header + "#endif\n")
            write(f"{directory}/Stage_{stage:02}.c", body)
    write("include/Rte_Mega.h", '#ifndef RTE_MEGA_H\n#define RTE_MEGA_H\n#include "Mega_Types.h"\n' + "".join(declarations) + "#endif\n")
    write("support/Rte_Memory.c", "".join(memory))
    write("app/Mega_Goal.c", """#include "Stage_00.h"
/* Target branch: trace pedal back through all stages to a controllable input. */
uint8 Mega_Goal(void)
{
    uint16 pedal = Mega_000_Stage_00();
    if (pedal == 0u) {
        return 0u;
    } else if (pedal >= 60u) {
        return 2u;
    } else {
        return 1u;
    }
}
""")
    write("runtime/Scenarios.c", f"""#include <stdio.h>
#include "Rte_Mega.h"
#include "Stage_{stages - 1:02}.h"
uint8 Mega_Goal(void);
static int check(uint16 raw, uint8 quality, uint8 expected)
{{
    (void)Rte_Write_Mega000_Pedal(0u);
    g_Stimulus_000.raw = raw;
    g_Stimulus_000.quality = quality;
    g_Stimulus_000.enabled = 1u;
    g_ReadFailure_000 = 0u;
    Mega_000_Publish();
    return Mega_Goal() == expected;
}}
int main(void)
{{
    if (!check(29u, 1u, 1u)) {{ return 1; }}
    if (!check(30u, 1u, 2u)) {{ return 2; }}
    if (!check(49u, 2u, 1u)) {{ return 3; }}
    if (!check(50u, 2u, 2u)) {{ return 4; }}
    if (!check(30u, 0u, 0u)) {{ return 5; }}
    if (!check(80u, 1u, 2u)) {{ return 6; }}
    g_Stimulus_000.enabled = 0u;
    g_Stimulus_000.raw = 0u;
    Mega_000_Publish();
    if (Mega_Goal() != 2u) {{ return 7; }} /* old buffer retained */
    g_ReadFailure_000 = 1u;
    if (Mega_Goal() != 0u) {{ return 8; }}
    g_ReadFailure_000 = 0u;
    (void)Rte_Write_Mega000_Pedal(0u); /* consumer before publisher */
    if (Mega_Goal() != 0u) {{ return 9; }}
    puts("PASS mega AUTOSAR: 9 scenarios");
    return 0;
}}
""")
    sources = sorted(path for path in output.rglob("*") if path.suffix in (".c", ".h"))
    manifest = {"synthetic": True, "components": components, "stages": stages,
                "c_files": sum(p.suffix == ".c" for p in sources),
                "h_files": sum(p.suffix == ".h" for p in sources),
                "source_bytes": sum(p.stat().st_size for p in sources),
                "target": "app/Mega_Goal.c", "runtime_scenarios": 9,
                "suggested_max_files": len(sources),
                "scoped_paths": ["app", "include", "components/Mega_000", "support"],
                "limits": "Synthetic name-based RTE candidates; wiring and runnable order are not inferred."}
    write("manifest.json", json.dumps(manifest, indent=2) + "\n")
    write("README.md", """# Synthetic AUTOSAR investigation workspace

Start at app/Mega_Goal.c: the pedal >= 60u branch.
Follow Mega_000_Stage_00 through the final stage, then Rte_Read_Channel(&pedal).
The independent Mega_000_Publish runnable writes the same channel.
Its source is g_Stimulus_000.raw; enabled and quality select whether/how it writes.
quality=1: raw*2. quality=2: raw+10. Disabled retains prior RTE memory.
The runtime harness supplies publisher-before-consumer order explicitly.

Set analysisPaths=["."] and analysisMaxFiles to manifest.suggested_max_files
or higher (6000 works for the default fixture), and select your installed engine
Python in user settings. For a smaller scope use manifest.scoped_paths.
RTE matching is a name-based candidate, not wiring/order/CT execution proof.
Do not analyze the parent repository or mix this workspace with other samples.
See the repository test/mega_autosar/README.md for commands and limitations.
""")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--components", type=int, default=64)
    parser.add_argument("--stages", type=int, default=40)
    args = parser.parse_args()
    root = generate_project(args.output, components=args.components, stages=args.stages)
    print((root / "manifest.json").read_text(encoding="ascii"))
