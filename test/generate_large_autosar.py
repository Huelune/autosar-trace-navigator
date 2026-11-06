"""Generate only synthetic C into a NEW directory; never overwrite source files."""

import argparse
import json
from pathlib import Path


DOMAINS = ("Brake", "Steering", "Battery", "Thermal", "Lighting", "Door",
           "Seat", "Wiper", "Cluster", "Cruise", "Parking", "Charging")


def generate(output: Path, components: int = 24) -> dict:
    """Build a deterministic, standalone C99 project with no third-party sources."""
    if type(components) is not int or not 1 <= components <= 256:
        raise ValueError("components must be between 1 and 256")
    output.mkdir(parents=True, exist_ok=False)
    files = []

    def write(name: str, content: str) -> None:
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = "\n".join(line.rstrip() for line in content.strip().splitlines()) + "\n"
        path.write_text(normalized, encoding="utf-8", newline="\n")
        files.append(name)

    write("shared/Std_Types.h", """
#ifndef LARGE_STD_TYPES_H
#define LARGE_STD_TYPES_H
#include <stdint.h>
typedef uint8_t uint8;
typedef uint16_t uint16;
typedef uint8 Std_ReturnType;
#define E_OK ((Std_ReturnType)0u)
#define E_NOT_OK ((Std_ReturnType)1u)
#define SENSOR_TO_UNIT(raw) ((raw) / 10)
enum { MODE_NORMAL = 1, MODE_ACTIVE = 2, MODE_FAULT = 3 };
#endif
""")
    declarations = []
    implementations = []
    cases = []
    metadata = []
    for index in range(components):
        name = f"{DOMAINS[index % len(DOMAINS)]}_{index:03}"
        threshold = 20 + (index % 5) * 5
        directory = f"swc/{name}"
        functions = ("10ms", "Evaluate", "Decide", "Eligible", "Validated", "Decode", "Read",
                     "Producer", "AcquireRaw", "AcquireDemand", "Diagnostic")
        declarations.append(f"void {name}_10ms(void);\nvoid {name}_Producer(void);")
        write(f"{directory}/{name}.h", f"""
#ifndef {name.upper()}_H
#define {name.upper()}_H
#include "../../shared/Std_Types.h"
void {name}_10ms(void);
void {name}_Producer(void);
uint16 {name}_AcquireRaw(void);
uint8 {name}_AcquireDemand(void);
{chr(10).join(f'int {name}_{suffix}(void);' for suffix in functions[1:7])}
int {name}_Diagnostic(int value);
uint16 Platform_ReadRaw(unsigned int index);
uint8 Platform_ReadDemand(unsigned int index);
#endif
""")
        api_specs = (("Read", "Signal_Raw", "uint16 *value", "*value = raw_buffer[{i}];", "raw_status"),
                     ("Read", "Demand_Percent", "uint8 *value", "*value = demand_buffer[{i}];", "demand_status"),
                     ("Write", "Signal_Raw", "uint16 value", "raw_buffer[{i}] = value;", None),
                     ("Write", "Demand_Percent", "uint8 value", "demand_buffer[{i}] = value;", None),
                     ("Write", "Mode", "uint8 value", "last_mode[{i}] = value; ++mode_writes[{i}];", None))
        apis = []
        for direction, signal, parameter, body, status in api_specs:
            api = f"Rte_{direction}_{name}_{signal}"
            alias = direction == "Read" and ((index % 4 == 0 and signal == "Signal_Raw") or
                                             (index % 4 == 1 and signal == "Demand_Percent"))
            implementation = f"Rte_Impl_{direction}_{name}_{signal}" if alias else api
            apis.append(f"Std_ReturnType {implementation}({parameter});")
            if alias:
                apis.append(f"#define {api}(p) {implementation}(p)" if signal == "Signal_Raw" else
                            f"#define {api} {implementation}")
            status_guard = f"if ({status}[{index}] != E_OK) return {status}[{index}];" if status else ""
            implementations.append(f"Std_ReturnType {implementation}({parameter})\n{{\n"
                                   f"    {status_guard}\n    {body.format(i=index)}\n    return E_OK;\n}}")
        write(f"{directory}/Rte_{name}.h", f"""
#ifndef RTE_{name.upper()}_H
#define RTE_{name.upper()}_H
/* Synthetic generated-style declarations, not vendor code. */
#include "{name}.h"
{chr(10).join(apis)}
#endif
""")
        write(f"{directory}/Control.c", f"""
#include "{name}.h"
#include "Rte_{name}.h"
void {name}_10ms(void)
{{
    int mode = {name}_Evaluate();
    if (mode == MODE_FAULT) {{
        (void)Rte_Write_{name}_Mode((uint8)MODE_FAULT);
    }} else if (mode == MODE_ACTIVE) {{
        /* TARGET: preserve this goal while following six call edges. */
        (void)Rte_Write_{name}_Mode((uint8)MODE_ACTIVE);
    }} else {{
        (void)Rte_Write_{name}_Mode((uint8)MODE_NORMAL);
    }}
}}
int {name}_Evaluate(void)
{{
    int request = {name}_Decide();
    if (request < 0) {{
        (void){name}_Diagnostic(request);
        return MODE_FAULT;
    }} else if (request == 1) {{
        return MODE_ACTIVE;
    }} else {{
        return MODE_NORMAL;
    }}
}}
""")
        write(f"{directory}/Decision.c", f"""
#include "{name}.h"
#include "Rte_{name}.h"
int {name}_Decide(void)
{{
    int eligible = {name}_Eligible();
    uint8 demand = 0u;
    if (eligible < 0) return -1;
    else if (Rte_Read_{name}_Demand_Percent(&demand) != E_OK) return -1;
    else if (demand > 100u) return -1;
    else {{
        if ((eligible == 1) && (demand >= 60u)) return 1;
        else return 0;
    }}
}}
int {name}_Eligible(void)
{{
    int value = {name}_Validated();
    if (value < 0) return -1;
    else if (value >= {threshold}) return 1;
    else return 0;
}}
""")
        write(f"{directory}/Signal.c", f"""
#include "{name}.h"
#include "Rte_{name}.h"
/* Intentionally identical static name in different translation units. */
static int Normalize(int raw)
{{
    return SENSOR_TO_UNIT(raw);
}}
int {name}_Validated(void)
{{
    int value = {name}_Decode();
    if (value < 0) return -1;
    else if (value > 250) return -1;
    else return value;
}}
int {name}_Decode(void)
{{
    int raw = {name}_Read();
    if (raw < 0) return -1;
    else if (raw == 65535) return -1;
    else return Normalize(raw);
}}
int {name}_Read(void)
{{
    uint16 raw = 0u;
    if (Rte_Read_{name}_Signal_Raw(&raw) != E_OK) return -1;
    else return (int)raw;
}}
""")
        backup = f"""
void {name}_BackupProducer(void)
{{
    (void)Rte_Write_{name}_Signal_Raw(0u);
}}
""" if index % 6 == 0 else ""
        write(f"{directory}/Producer.c", f"""
#include "{name}.h"
#include "Rte_{name}.h"
void {name}_Producer(void)
{{
    (void)Rte_Write_{name}_Signal_Raw({name}_AcquireRaw());
    (void)Rte_Write_{name}_Demand_Percent({name}_AcquireDemand());
}}
uint16 {name}_AcquireRaw(void) {{ return Platform_ReadRaw({index}u); }}
uint8 {name}_AcquireDemand(void) {{ return Platform_ReadDemand({index}u); }}
{backup}
""")
        diagnostic = f"""
int {name}_Diagnostic(int value)
{{
    switch (value) {{
    case -1: return 1;
    case 0: return 0;
    default:
        if (value > 0) return 2;
        else return 3;
    }}
}}
""" if index % 3 == 0 else f"""
int {name}_Diagnostic(int value)
{{
    int count = 0;
    int i;
    for (i = 0; i < 3; ++i) {{
        if (value < i) ++count;
        else if (value == i) count += 2;
        else count += 3;
    }}
    return count;
}}
"""
        if index % 4 == 0:
            diagnostic = f"#if defined(LARGE_TEST_EXTRA)\nint {name}_Diagnostic(int value) {{ return value; }}\n#else\n{diagnostic}\n#endif"
        write(f"{directory}/Diagnostics.c", f'#include "{name}.h"\n{diagnostic}')
        for raw, demand, raw_ok, demand_ok, expected in (
            (threshold * 10, 60, True, True, "MODE_ACTIVE"),
            (threshold * 10 - 1, 60, True, True, "MODE_NORMAL"),
            (threshold * 10, 59, True, True, "MODE_NORMAL"),
            (2510, 60, True, True, "MODE_FAULT"), (65535, 60, True, True, "MODE_FAULT"),
            (threshold * 10, 101, True, True, "MODE_FAULT"),
            (threshold * 10, 60, False, True, "MODE_FAULT"),
            (threshold * 10, 60, True, False, "MODE_FAULT"),
        ):
            cases.append(f'    {{"{name}", {index}u, {raw}u, {demand}u, '
                         f'{"E_OK" if raw_ok else "E_NOT_OK"}, {"E_OK" if demand_ok else "E_NOT_OK"}, '
                         f'{expected}, {name}_Producer, {name}_10ms}},')
        metadata.append({"name": name, "threshold": threshold, "scope": directory,
                         "trace": [f"{name}_{suffix}" for suffix in functions[:7]],
                         "backup_producer": index % 6 == 0})

    write("support/Rte_Stub.c", f"""
#include "../shared/Std_Types.h"
#define COMPONENT_COUNT {components}u
static uint16 hardware_raw[COMPONENT_COUNT], raw_buffer[COMPONENT_COUNT];
static uint8 hardware_demand[COMPONENT_COUNT], demand_buffer[COMPONENT_COUNT], last_mode[COMPONENT_COUNT];
static Std_ReturnType raw_status[COMPONENT_COUNT], demand_status[COMPONENT_COUNT];
static unsigned int mode_writes[COMPONENT_COUNT];
void Platform_Setup(unsigned int index, uint16 raw, uint8 demand,
                    Std_ReturnType raw_ok, Std_ReturnType demand_ok)
{{
    hardware_raw[index] = raw;
    hardware_demand[index] = demand;
    raw_status[index] = raw_ok;
    demand_status[index] = demand_ok;
    raw_buffer[index] = 0u;
    demand_buffer[index] = 0u;
    last_mode[index] = 0u;
    mode_writes[index] = 0u;
}}
uint16 Platform_ReadRaw(unsigned int index) {{ return hardware_raw[index]; }}
uint8 Platform_ReadDemand(unsigned int index) {{ return hardware_demand[index]; }}
uint8 Platform_Mode(unsigned int index) {{ return last_mode[index]; }}
unsigned int Platform_Writes(unsigned int index) {{ return mode_writes[index]; }}
{chr(10).join(implementations)}
""")
    write("support/test_project.c", f"""
#include <stdio.h>
#include "../shared/Std_Types.h"
{chr(10).join(declarations)}
void Platform_Setup(unsigned int index, uint16 raw, uint8 demand, Std_ReturnType raw_ok, Std_ReturnType demand_ok);
uint8 Platform_Mode(unsigned int index);
unsigned int Platform_Writes(unsigned int index);
typedef struct {{
    const char *name;
    unsigned int index;
    uint16 raw;
    uint8 demand;
    Std_ReturnType raw_ok, demand_ok;
    uint8 expected;
    void (*produce)(void);
    void (*consume)(void);
}} TestCase;
int main(void)
{{
    const TestCase cases[] = {{
{chr(10).join(cases)}
    }};
    unsigned int index;
    unsigned int count = (unsigned int)(sizeof(cases) / sizeof(cases[0]));
    for (index = 0u; index < count; ++index) {{
        const TestCase *item = &cases[index];
        Platform_Setup(item->index, item->raw, item->demand, item->raw_ok, item->demand_ok);
        item->produce();
        item->consume();
        if (Platform_Mode(item->index) != item->expected || Platform_Writes(item->index) != 1u) {{
            fprintf(stderr, "FAIL %s case %u mode=%u\\n", item->name, index, (unsigned int)Platform_Mode(item->index));
            return 1;
        }}
    }}
    printf("PASS large AUTOSAR: %u scenarios\\n", count);
    return 0;
}}
""")
    manifest = {"components": metadata, "c_files": sum(f.endswith(".c") for f in files),
                "h_files": sum(f.endswith(".h") for f in files), "runtime_scenarios": len(cases)}
    write("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    write("README.md", f"""# 확장 가상 AUTOSAR 프로젝트

test/generate_large_autosar.py로 생성한 독립 C99 fixture다. 실제 차량 동작 모델이나
벤더 AUTOSAR 생성물이 아니며, 여러 SWC의 제어/판단/신호/공급/진단 탐색을 모사한다.
이 변형은 {components} SWC, C {manifest['c_files']}개 + H {manifest['h_files']}개,
실행 시나리오 {len(cases)}개다.

GUI 루트는 이 폴더를 선택하고, 범위는 swc/Brake_000;shared부터 시작한다.
함수명 Brake_000_10ms를 검색하고 MODE_ACTIVE else-if를 목표로 선택한다.
manifest.json에 각 SWC의 6단계 호출 경로와 입력 threshold가 있다.
RTE 후보는 제어/신호 범위만 선택했을 때와 Producer.c를 포함했을 때를 비교한다.
swc 범위를 넓히면 Normalize 동명 static 후보와 일부 백업 공급자의 모호성이 나타난다.
공급·소비·실행 순서가 확정된다는 뜻은 아니다.

소스는 편집하지 않고, 변형은 생성기를 새 폴더에 실행하여 만든다.
루트 범위 . 은 {manifest['c_files'] + manifest['h_files']}파일이다. 80 SWC 변형은 563파일로
전체 범위 기본 500파일 제한을 넘으므로 일부 SWC를 선택해 분석해야 한다.
""")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="new, non-existing output directory")
    parser.add_argument("--components", type=int, default=24)
    args = parser.parse_args()
    manifest = generate(args.output, args.components)
    print(f"Generated {manifest['c_files']} C + {manifest['h_files']} H; "
          f"{manifest['runtime_scenarios']} runtime scenarios")


if __name__ == "__main__":
    main()
