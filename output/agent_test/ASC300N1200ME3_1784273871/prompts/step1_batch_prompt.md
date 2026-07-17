# Agent 1: Table Row Classifier

## 任务

你是一个 SiC MOSFET 模块 datasheet 参数分类器。

给定一行 Camelot 提取的 datasheet 表格数据，你需要判断：
1. 这行是否包含目标参数
2. 参数的具体类型
3. 参数值、单位、条件

## 目标参数列表

只识别以下 5 个参数：

| field_id | 英文名 | 中文名 | 典型符号 |
|----------|--------|--------|----------|
| voltage_rating | Drain-Source Voltage | 漏源电压 | VDS |
| current_rating | Drain Current | 漏极电流 | ID |
| rds_on_25c | RDS(on) @25°C | 导通电阻 @25°C | RDS(on) |
| vgs_th | Gate Threshold Voltage | 门极阈值电压 | VGS(th) |
| trr | Reverse Recovery Time | 反向恢复时间 | tRR, trr |

## 输入格式

```json
{
  "page_number": 1,
  "table_index": 1,
  "row_index": 2,
  "row_cells": ["VDS", "Drain-Source Voltage", "1200", "", "", "V", "TC=25°C"],
  "nearby_header": ["Symbol", "Parameter", "Min.", "Typ.", "Max.", "Unit", "Test Conditions"]
}
```

## 输出格式

输出严格 JSON，不要 markdown：

```json
{
  "is_target_parameter": true/false,
  "field_id": "voltage_rating" / null,
  "confidence": 0.0-1.0,
  "extracted_values": {
    "min": null,
    "typ": null,
    "max": null,
    "value": 1200
  },
  "unit": "V",
  "condition": "TC=25°C",
  "reasoning": "为什么判断这是/不是目标参数",
  "source_cells": [0, 2, 5, 6],
  "warnings": []
}
```

## 判断标准

### voltage_rating (VDS)
- 符号列包含 "VDS" 或 "Drain-Source Voltage"
- 单位是 V 或 kV
- 通常在 "Absolute Maximum Ratings" 部分
- 值通常是 1200V, 1700V 等

### current_rating (ID)
- 符号列包含 "ID" 或 "Drain Current"
- 单位是 A
- 通常有 "continuous" 或 "pulsed" 标注
- 条件通常包含 TC=25°C 或 TC=75°C

### rds_on_25c
- 符号列包含 "RDS(on)" 或 "Static Drain-Source on Resistance"
- 单位是 mΩ
- 条件必须包含 TC=25°C（或无温度条件时默认为 25°C）
- 值通常是 typ 和 max 两个（如 5.3 / 6.7 mΩ）

### vgs_th
- 符号列包含 "VGS(th)" 或 "Gate Threshold Voltage"
- 单位是 V
- 值通常是一个范围（如 2-4 V）
- 条件通常是 VDS=VGS 或 VDS=VGS; ID=xxmA

### trr
- 符号列包含 "tRR" 或 "trr" 或 "Reverse Recovery Time"
- 单位是 ns
- 条件通常包含 IF、VR、RG、Load

## 注意事项

1. **不要编造值** - 只提取 row_cells 中明确存在的数据
2. **注意表头结构** - 同一列可能跨行，表头在上一行
3. **处理合并单元格** - Camelot lattice 模式有时会分离单元格
4. **条件提取** - 从最后一列或倒数第二列提取条件
5. **返回 source_cells** - 说明值来自哪些列，便于追溯

## 示例

### 示例 1: VDS
输入: `["VDS", "Drain-Source Voltage", "1200", "", "", "V", "TC=25°C"]`
输出:
```json
{
  "is_target_parameter": true,
  "field_id": "voltage_rating",
  "confidence": 0.95,
  "extracted_values": {"min": null, "typ": null, "max": null, "value": 1200},
  "unit": "V",
  "condition": "TC=25°C",
  "reasoning": "符号列包含 VDS，值 1200V 在 VDS 典型范围内",
  "source_cells": [0, 2, 5, 6],
  "warnings": []
}
```

### 示例 2: RDS(on)
输入: `["RDS(on)", "Static Drain-Source on Resistance", "", "5.3", "6.7", "mΩ", "VGS=18V; ID=150A; TC=25°C"]`
输出:
```json
{
  "is_target_parameter": true,
  "field_id": "rds_on_25c",
  "confidence": 0.9,
  "extracted_values": {"min": null, "typ": 5.3, "max": 6.7, "value": null},
  "unit": "mΩ",
  "condition": "VGS=18V; ID=150A; TC=25°C",
  "reasoning": "符号包含 RDS(on)，值 5.3/6.7 mΩ，条件包含 TC=25°C",
  "source_cells": [0, 3, 4, 5, 6],
  "warnings": ["typ 在第4列, max 在第5列"]
}
```

### 示例 3: 非目标参数
输入: `["QG", "Total Gate Charge", "", "618", "", "nC", "VDD=800V; VGS=-5/+18V; ID=150A"]`
输出:
```json
{
  "is_target_parameter": false,
  "field_id": null,
  "confidence": 0.0,
  "extracted_values": null,
  "unit": "nC",
  "condition": "VDD=800V; VGS=-5/+18V; ID=150A",
  "reasoning": "QG 不在目标参数列表中（prototype v0.1 只测试 5 个参数）",
  "source_cells": [0, 3, 5, 6],
  "warnings": ["不在测试范围内"]
}
```


# LLM INPUT
# INPUT DATA

Document: ASC300N1200ME3.pdf


## Page 1, Table 0 (flavor=lattice, score=100.0)
  ROW[0]: ['Symbol', 'Parameter', 'Values', '', '', 'Unit', 'Test Conditions']
  ROW[1]: ['Absolute maximum rating', '', '', '', '', '', '']
  ROW[2]: ['VDS', 'Drain-Source Voltage', '1200', '', '', 'V', 'TC=25\uf0b0C']
  ROW[3]: ['ID', 'Drain Current (continuous)', '300', '', '', 'A', 'TC=25\uf0b0C']
  ROW[4]: ['', '', '240', '', '', '', 'TC=75\uf0b0C']
  ROW[5]: ['TJ; MAX', 'Junction Temperature', '175', '', '', '\uf0b0C', '']
  ROW[6]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[7]: ['Static characteristics', '', '', '', '', '', '']
  ROW[8]: ['RDS(on)', 'Static Drain-Source on Resistance', '-', '5.3', '6.7', 'mΩ', 'VGS=18V; ID=150A; TC=25\uf0b0C']
  ROW[9]: ['Dynamic characteristics', '', '', '', '', '', '']
  ROW[10]: ['QG', 'Total Gate Charge', '-', '618', '-', 'nC', 'VDD=800V; VGS=-5/+18V; ID=150A; TC=25\uf0b0C']
  ROW[11]: ['QGD', 'Gate-Drain Charge', '-', '147', '-', '', '']
  ROW[12]: ['Source-drain diode', '', '', '', '', '', '']
  ROW[13]: ['QRR', 'Reverse Recovery Charge', '-', '1839', '-', 'nC', 'VGS=-5/+18V; IF=150A; VR=800V; RG(ext)=5Ω; Load=50µH; TJ=25\uf0b0C']

## Page 1, Table 1 (flavor=stream, score=95.0)
  ROW[0]: ['Key Parameters', '', '', '', '', '', '', '']
  ROW[1]: ['Symbol', 'Parameter', '', 'Values', '', 'Unit', '', 'Test Conditions']
  ROW[2]: ['Absolute maximum rating', '', '', '', '', '', '', '']
  ROW[3]: ['VDS', 'Drain-Source Voltage', '', '1200', '', 'V', 'TC=25\uf0b0C', '']
  ROW[4]: ['', '', '', '300', '', '', 'TC=25\uf0b0C', '']
  ROW[5]: ['ID', 'Drain Current (continuous)', '', '', '', 'A', '', '']
  ROW[6]: ['', '', '', '240', '', '', 'TC=75\uf0b0C', '']
  ROW[7]: ['TJ; MAX', 'Junction Temperature', '', '175', '', '\uf0b0C', '', '']
  ROW[8]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', '', 'Test Conditions']
  ROW[9]: ['Static characteristics', '', '', '', '', '', '', '']
  ROW[10]: ['RDS(on)', 'Static Drain-Source on Resistance', '-', '5.3', '6.7', 'mΩ', 'VGS=18V; ID=150A; TC=25\uf0b0C', '']
  ROW[11]: ['Dynamic characteristics', '', '', '', '', '', '', '']
  ROW[12]: ['QG', 'Total Gate Charge', '-', '618', '-', '', '', '']
  ROW[13]: ['', '', '', '', '', '', '', 'VDD=800V; VGS=-5/+18V; ID=150A;']
  ROW[14]: ['', '', '', '', '', 'nC', '', '']
  ROW[15]: ['', '', '', '', '', '', 'TC=25\uf0b0C', '']
  ROW[16]: ['QGD', 'Gate-Drain Charge', '-', '147', '-', '', '', '']
  ROW[17]: ['Source-drain diode', '', '', '', '', '', '', '']
  ROW[18]: ['', '', '', '', '', '', '', 'VGS=-5/+18V; IF=150A; VR=800V;']
  ROW[19]: ['QRR', 'Reverse Recovery Charge', '-', '1839', '-', 'nC', '', '']
  ROW[20]: ['', '', '', '', '', '', '', 'RG(ext)=5Ω; Load=50µH; TJ=25\uf0b0C']

## Page 1, Table 2 (flavor=lattice, score=85.0)
  ROW[0]: ['Order Number', 'ASC300N1200ME3-X']
  ROW[1]: ['Marking', 'ASC300N1200ME3']
  ROW[2]: ['Package Type', 'ME3']

## Page 2, Table 0 (flavor=lattice, score=112.0)
  ROW[0]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[1]: ['Static characteristics (at TC=25℃ unless otherwise specified)', '', '', '', '', '', '']
  ROW[2]: ['BVDS', 'Drain-Source Breakdown Voltage', '1200', '-', '-', 'V', 'VGS=0V']
  ROW[3]: ['IDSS', 'Zero Gate Voltage Drain Current', '-', '-', '150', 'μA', 'VDS=1200V; VGS=0V']
  ROW[4]: ['IGSS', 'Gate-Body Leakage Current', '-', '-', '1.5', 'μA', 'VGS=-10/20V; VDS=0V']
  ROW[5]: ['VGS(th)', 'Gate Threshold Voltage', '2', '-', '4', 'V', 'VDS=VGS; ID=30mA']
  ROW[6]: ['RDS(on)', 'Static Drain-Source on Resistance', '-', '5.3', '6.7', 'mΩ', 'VGS=18V; ID=150A']
  ROW[7]: ['VGS(on)', 'Recommended Turn-on Voltage', '-', '18', '-', 'V', 'Static']
  ROW[8]: ['VGS(off)', 'Recommended Turn-off Voltage', '-', '-5', '-', '', '']
  ROW[9]: ['RG', 'Gate Resistance', '-', '2.3', '-', 'Ω', 'VGS=0V; f=1MHz']
  ROW[10]: ['Dynamic characteristics (at TC=25℃ unless otherwise specified)', '', '', '', '', '', '']
  ROW[11]: ['Ciss', 'Input Capacitance', '-', '9.15', '-', 'nF', 'VDS=1000V; f=1MHz; VAC=25mV']
  ROW[12]: ['Coss', 'Output Capacitance', '-', '0.29', '-', '', '']
  ROW[13]: ['Crss', 'Reverse Transfer Capacitance', '-', '45', '-', 'pF', '']
  ROW[14]: ['Eon', 'Turn-on Energy', '-', '7.1', '-', 'mJ', 'VDS=800V; VGS=-5/+18V; ID=150A; RG(ext)=5Ω; Load=50µH']
  ROW[15]: ['Eoff', 'Turn-off Energy', '-', '7.9', '-', '', '']
  ROW[16]: ['QGS', 'Gate-Source Charge', '-', '174', '-', 'nC', 'VDD=800V; VGS=-5/+18V; ID=150A']
  ROW[17]: ['QGD', 'Gate-Drain Charge', '-', '147', '-', '', '']
  ROW[18]: ['QG', 'Total Gate Charge', '-', '618', '-', '', '']
  ROW[19]: ['td(on)', 'Turn-on Delay Time', '-', '186', '-', 'ns', 'VDS=800V; VGS=-5/+18V; ID=150A; RG(ext)=5Ω; Load=50µH']
  ROW[20]: ['tr', 'Rise Time', '-', '42', '-', '', '']
  ROW[21]: ['td(off)', 'Turn-off Delay Time', '-', '387', '-', '', '']
  ROW[22]: ['tf', 'Fall Time', '-', '86', '-', '', '']

## Page 2, Table 1 (flavor=stream, score=110.0)
  ROW[0]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[1]: ['Static characteristics (at TC=25℃ unless otherwise specified)', '', '', '', '', '', '']
  ROW[2]: ['BVDS', 'Drain-Source Breakdown Voltage', '1200', '-', '-', 'V', 'VGS=0V']
  ROW[3]: ['IDSS', 'Zero Gate Voltage Drain Current', '-', '-', '150', 'μA', 'VDS=1200V; VGS=0V']
  ROW[4]: ['IGSS', 'Gate-Body Leakage Current', '-', '-', '1.5', 'μA', 'VGS=-10/20V; VDS=0V']
  ROW[5]: ['VGS(th)', 'Gate Threshold Voltage', '2', '-', '4', 'V', 'VDS=VGS; ID=30mA']
  ROW[6]: ['RDS(on)', 'Static Drain-Source on Resistance', '-', '5.3', '6.7', 'mΩ', 'VGS=18V; ID=150A']
  ROW[7]: ['VGS(on)', 'Recommended Turn-on Voltage', '-', '18', '-', '', '']
  ROW[8]: ['', '', '', '', '', 'V', 'Static']
  ROW[9]: ['VGS(off)', 'Recommended Turn-off Voltage', '-', '-5', '-', '', '']
  ROW[10]: ['RG', 'Gate Resistance', '-', '2.3', '-', 'Ω', 'VGS=0V; f=1MHz']
  ROW[11]: ['Dynamic characteristics (at TC=25℃ unless otherwise specified)', '', '', '', '', '', '']
  ROW[12]: ['Ciss', 'Input Capacitance', '-', '9.15', '-', '', '']
  ROW[13]: ['', '', '', '', '', 'nF', '']
  ROW[14]: ['Coss', 'Output Capacitance', '-', '0.29', '-', '', 'VDS=1000V; f=1MHz; VAC=25mV']
  ROW[15]: ['Crss', 'Reverse Transfer Capacitance', '-', '45', '-', 'pF', '']
  ROW[16]: ['Eon', 'Turn-on Energy', '-', '7.1', '-', '', '']
  ROW[17]: ['', '', '', '', '', '', 'VDS=800V; VGS=-5/+18V; ID=150A;']
  ROW[18]: ['', '', '', '', '', 'mJ', '']
  ROW[19]: ['', '', '', '', '', '', 'RG(ext)=5Ω; Load=50µH']
  ROW[20]: ['Eoff', 'Turn-off Energy', '-', '7.9', '-', '', '']
  ROW[21]: ['QGS', 'Gate-Source Charge', '-', '174', '-', '', '']
  ROW[22]: ['QGD', 'Gate-Drain Charge', '-', '147', '-', 'nC', 'VDD=800V; VGS=-5/+18V; ID=150A']
  ROW[23]: ['QG', 'Total Gate Charge', '-', '618', '-', '', '']
  ROW[24]: ['td(on)', 'Turn-on Delay Time', '-', '186', '-', '', '']
  ROW[25]: ['tr', 'Rise Time', '-', '42', '-', '', '']
  ROW[26]: ['', '', '', '', '', '', 'VDS=800V; VGS=-5/+18V; ID=150A;']
  ROW[27]: ['', '', '', '', '', 'ns', '']
  ROW[28]: ['', '', '', '', '', '', 'RG(ext)=5Ω; Load=50µH']
  ROW[29]: ['td(off)', 'Turn-off Delay Time', '-', '387', '-', '', '']
  ROW[30]: ['tf', 'Fall Time', '-', '86', '-', '', '']

## Page 2, Table 2 (flavor=lattice, score=104.4)
  ROW[0]: ['Symbol', 'Parameter', 'Values', 'Unit']
  ROW[1]: ['VDS', 'Drain-Source Voltage', '1200', 'V']
  ROW[2]: ['VGS', 'Gate-Source Voltage (dynamic)', '-10/+22', 'V']
  ROW[3]: ['ID', 'Drain Current (continuous; TC=25\uf0b0C)', '300', 'A']
  ROW[4]: ['', 'Drain Current (continuous; TC=75\uf0b0C)', '240', '']
  ROW[5]: ['IDM', 'Drain Current (pulsed)', '480', 'A']
  ROW[6]: ['Top; Tstg', 'Operating and Storage Temperature Range', '-40 to +150', '\uf0b0C']
  ROW[7]: ['TJ; MAX', 'Junction Temperature', '175', '\uf0b0C']
  ROW[8]: ['Rth Jh', 'Thermal Resistance, Junction-to-Heatsink', '0.12', '\uf0b0C/W']

## Page 2, Table 3 (flavor=stream, score=95.0)
  ROW[0]: ['', 'bsolute Maximum Ratings (at TC=25℃ unless otherwise specified)', '', '']
  ROW[1]: ['Symbol', 'Parameter', 'Values', 'Unit']
  ROW[2]: ['VDS', 'Drain-Source Voltage', '1200', 'V']
  ROW[3]: ['VGS', 'Gate-Source Voltage (dynamic)', '-10/+22', 'V']
  ROW[4]: ['', 'Drain Current (continuous; TC=25\uf0b0C)', '300', '']
  ROW[5]: ['ID', '', '', 'A']
  ROW[6]: ['', 'Drain Current (continuous; TC=75\uf0b0C)', '240', '']
  ROW[7]: ['IDM', 'Drain Current (pulsed)', '480', 'A']
  ROW[8]: ['Top; Tstg', 'Operating and Storage Temperature Range', '-40 to +150', '\uf0b0C']
  ROW[9]: ['TJ; MAX', 'Junction Temperature', '175', '\uf0b0C']
  ROW[10]: ['Rth Jh', 'Thermal Resistance, Junction-to-Heatsink', '0.12', '\uf0b0C/W']

## Page 2, Table 4 (flavor=stream, score=70.0)
  ROW[0]: ['Eon', 'Turn-on Energy', '-', '7.1', '-', '']
  ROW[1]: ['', '', '', '', '', 'mJ']
  ROW[2]: ['Eoff', 'Turn-off Energy', '-', '7.9', '-', '']
  ROW[3]: ['QGS', 'Gate-Source Charge', '-', '174', '-', '']
  ROW[4]: ['QGD', 'Gate-Drain Charge', '-', '147', '-', 'nC']
  ROW[5]: ['QG', 'Total Gate Charge', '-', '618', '-', '']
  ROW[6]: ['td(on)', 'Turn-on Delay Time', '-', '186', '-', '']
  ROW[7]: ['tr', 'Rise Time', '-', '42', '-', '']
  ROW[8]: ['', '', '', '', '', 'ns']
  ROW[9]: ['td(off)', 'Turn-off Delay Time', '-', '387', '-', '']

## Page 3, Table 0 (flavor=lattice, score=125.2)
  ROW[0]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[1]: ['VFSD', 'Forward Voltage', '-', '3.5', '6', 'V', 'VGS=0V; IF=150A']
  ROW[2]: ['IS', 'Continuous Diode Forward Current', '-', '150', '-', 'A', 'VGS=0V; TC=25\uf0b0C']
  ROW[3]: ['tRR', 'Reverse Recovery Time', '-', '96', '-', 'ns', 'VGS=-5/+18V; IF=150A; VR=800V; RG(ext)=5Ω; Load=50µH']
  ROW[4]: ['QRR', 'Reverse Recovery Charge', '-', '1839', '-', 'nC', '']
  ROW[5]: ['IRRM', 'Peak Reverse Recovery Current', '-', '141', '-', 'A', '']

## Page 3, Table 1 (flavor=lattice, score=113.9)
  ROW[0]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[1]: ['LStray', 'Stray Inductance', '-', '20', '-', 'nH', '']
  ROW[2]: ['W', 'Weight', '-', '340', '-', 'g', '']
  ROW[3]: ['Ms', 'Mounting Torque', '4.0', '-', '5.5', 'Nm', 'M6-1.0 Bolts']
  ROW[4]: ['Visol', 'Case Isolation Voltage (DC; t=1min)', '4.2', '-', '-', 'kV', '']
  ROW[5]: ['-', 'Clearance Distance', '-', '11', '-', 'mm', 'Terminal to Terminal']
  ROW[6]: ['', '', '-', '23', '-', 'mm', 'Terminal to Baseplate']
  ROW[7]: ['-', 'Creepage Distance', '-', '23', '-', 'mm', 'Terminal to Terminal']
  ROW[8]: ['', '', '-', '29', '-', 'mm', 'Terminal to Baseplate']

## Page 3, Table 2 (flavor=stream, score=110.0)
  ROW[0]: ['B', 'ody Diode Characteristics (at TJ=25℃ unless otherwise specified)', '', '', '', '', '', '']
  ROW[1]: ['', 'Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[2]: ['', 'VFSD', 'Forward Voltage', '-', '3.5', '6', 'V', 'VGS=0V; IF=150A']
  ROW[3]: ['', 'IS', 'Continuous Diode Forward Current', '-', '150', '-', 'A', 'VGS=0V; TC=25\uf0b0C']
  ROW[4]: ['', 'tRR', 'Reverse Recovery Time', '-', '96', '-', 'ns', '']
  ROW[5]: ['', '', '', '', '', '', '', 'VGS=-5/+18V; IF=150A; VR=800V;']
  ROW[6]: ['', 'QRR', 'Reverse Recovery Charge', '-', '1839', '-', 'nC', '']
  ROW[7]: ['', '', '', '', '', '', '', 'RG(ext)=5Ω; Load=50µH']
  ROW[8]: ['', 'IRRM', 'Peak Reverse Recovery Current', '-', '141', '-', 'A', '']

## Page 3, Table 3 (flavor=stream, score=110.0)
  ROW[0]: ['Module Physical Characteristics', '', '', '', '', '', '']
  ROW[1]: ['Symbol', 'Parameter', 'Min.', 'Typ.', 'Max.', 'Unit', 'Test Conditions']
  ROW[2]: ['LStray', 'Stray Inductance', '-', '20', '-', 'nH', '']
  ROW[3]: ['W', 'Weight', '-', '340', '-', 'g', '']
  ROW[4]: ['Ms', 'Mounting Torque', '4.0', '-', '5.5', 'Nm', 'M6-1.0 Bolts']
  ROW[5]: ['Visol', 'Case Isolation Voltage (DC; t=1min)', '4.2', '-', '-', 'kV', '']
  ROW[6]: ['', '', '-', '11', '-', 'mm', 'Terminal to Terminal']
  ROW[7]: ['-', 'Clearance Distance', '', '', '', '', '']
  ROW[8]: ['', '', '-', '23', '-', 'mm', 'Terminal to Baseplate']
  ROW[9]: ['', '', '-', '23', '-', 'mm', 'Terminal to Terminal']
  ROW[10]: ['-', 'Creepage Distance', '', '', '', '', '']
  ROW[11]: ['', '', '-', '29', '-', 'mm', 'Terminal to Baseplate']

## Page 4, Table 0 (flavor=stream, score=70.0)
  ROW[0]: ['', '600', '', '', '', '2']
  ROW[1]: ['', '', 'VGS=20V', 'VGS=18V', '', '']
  ROW[2]: ['', '', '', '', '', '1.8']
  ROW[3]: ['', '500', '', '', '', '']
  ROW[4]: ['', '', '', '', '', '1.6']
  ROW[5]: ['', '', '', '', '', '1.4']
  ROW[6]: ['', '', '', 'VGS=16V', '', '']
  ROW[7]: ['', '400', '', '', '', '']
  ROW[8]: ['', '', '', '', '', '1.2']
  ROW[9]: ['Drain-Source Current, IDS(A)', '300', '', '', 'On Resistance, RDS(on)', '1']
  ROW[10]: ['', '', '', 'VGS=12V', '', '']
  ROW[11]: ['', '', '', '', '', '0.8']
  ROW[12]: ['', '200', '', '', '', '']
  ROW[13]: ['', '', '', '', '', '0.6']
  ROW[14]: ['', '', '', '', '', '0.4']
  ROW[15]: ['', '100', '', '', '', '']
  ROW[16]: ['', '', '', 'VGS=8V', '', '']
  ROW[17]: ['', '', '', '', '', '0.2']

## Page 4, Table 1 (flavor=stream, score=70.0)
  ROW[0]: ['', '3.5', '', '600', '', '', '']
  ROW[1]: ['', '', '', '', 'VDS=20V', '', '']
  ROW[2]: ['', '3', '', '', '', '', '']
  ROW[3]: ['', '', '', '500', '', '', '']
  ROW[4]: ['', '2.5', '', '', '', '', '']
  ROW[5]: ['', '', '', '400', '', '', '']
  ROW[6]: ['', '2', '', '', '', '', '']
  ROW[7]: ['', '', '', '', '', 'TJ=175℃', '']
  ROW[8]: ['Threshold Voltage, Vth(V)', '', '', '300', '', '', '']
  ROW[9]: ['', '1.5', 'Drain-Source Current, IDS(A)', '', '', '', '']
  ROW[10]: ['', '', '', '', '', 'TJ=25℃', '']
  ROW[11]: ['', '', '', '200', '', '', '']
  ROW[12]: ['', '1', '', '', '', '', '']
  ROW[13]: ['', '', '', '', '', '', 'TJ=-55℃']
  ROW[14]: ['', '', '', '100', '', '', '']
  ROW[15]: ['', '0.5', '', '', '', '', '']

## Page 5, Table 0 (flavor=lattice, score=70.0)
  ROW[0]: ['25 20 15 10 Switching Loss (mJ) 5 0 0 40', '', '', '', '', '', '']
  ROW[1]: ['', 'VGS=-5/+18V VDS=800V L=100μH', '', '', '', '', '']
  ROW[2]: ['', 'RG(ext)=5Ω', '', '', '', 'Etotal', '']
  ROW[3]: ['', '', '', '', '', 'Eoff', '']
  ROW[4]: ['', '', '', '', '', 'Eon', '']
  ROW[5]: ['', '', '', '', '', '', '']
  ROW[6]: ['', '', '', '80 Drain-Source Current, IDS (A)', '120', '160 200', '']

## Page 5, Table 1 (flavor=stream, score=70.0)
  ROW[0]: ['', '', '', '', '', '', '', '', '20', '', '', '', '', '', '']
  ROW[1]: ['-5', '-4', '-3', '-2', '-1', '0', '', '', '', '', '', '', '', '', '']
  ROW[2]: ['', '', '', '', '', '', '0', '', '', '', '', '', '', '', '']
  ROW[3]: ['VGS=-5V', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
  ROW[4]: ['', '', '', '', '', '', '', '', '15', '', '', '', '', '', '']
  ROW[5]: ['', '', '', '', '', '', '-100', '', '', '', '', '', '', '', '']
  ROW[6]: ['', 'VGS=-2V', '', '', '', '', '', '', '', '', '', '', '', '', '']
  ROW[7]: ['', '', '', '', '', '', '-200', '', '', '', '', '', '', '', '']
  ROW[8]: ['', '', '', '', '', '', '', '', '10', '', '', '', '', '', '']
  ROW[9]: ['', '', 'VGS=0V', '', '', '', '', '', '', '', '', '', '', '', '']
  ROW[10]: ['', '', '', '', '', '', '-300', 'Gate-Source Voltage, VGS(V)', '', '', '', '', '', '', '']
  ROW[11]: ['', '', '', '', '', '', '', '', '5', '', '', '', '', '', '']
  ROW[12]: ['', '', '', '', '', '', '-400', '', '', '', '', '', '', '', '']
  ROW[13]: ['', '', '', '', '', '', '', '', '0', '', '', '', '', '', '']
  ROW[14]: ['', '', '', '', '', '', '-500', '', '', '', '', '', '', '', '']
  ROW[15]: ['', '', '', '', '', '', '', '', '-5', '', '', '', '', '', '']
  ROW[16]: ['', '', '', '', '', '', '', '', '', '0', '150', '300', '450', '600', '750']
  ROW[17]: ['', '', '', '', '', '', '-600', '', '', '', '', '', '', '', '']
  ROW[18]: ['Drain-Source Voltage, VDS (V)', '', '', '', '', '', '', '', '', '', '', 'Gate Charge, QG (nC)', '', '', '']

## Page 5, Table 2 (flavor=stream, score=70.0)
  ROW[0]: ['100000', '', '', '', '', '', '', '', '', '25', '', '', '', '', '']
  ROW[1]: ['', '', '', '', '', '', '', '', '', '', '', 'VGS=-5/+18V', '', '', '']
  ROW[2]: ['', '', '', '', '', '', '', '', '', '', '', 'VDS=800V', '', '', '']
  ROW[3]: ['', '', '', '', '', '', '', '', '', '', '', 'L=100μH', '', '', '']
  ROW[4]: ['', '', '', '', '', '', '', '', '', '20', '', 'RG(ext)=5Ω', '', '', '']
  ROW[5]: ['', '', '', '', '', '', 'CISS', '', '', '', '', '', '', '', '']
  ROW[6]: ['10000', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
  ROW[7]: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', 'Etotal']
  ROW[8]: ['', '', '', '', '', '', '', '', '', '15', '', '', '', '', '']
  ROW[9]: ['1000', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
  ROW[10]: ['Capacitance (pF)', '', '', '', '', '', '', '', '', 'Switching Loss (mJ)', '', '', '', '', 'Eoff']
  ROW[11]: ['', '', '', '', '', '', 'COSS', '', '', '10', '', '', '', '', '']
  ROW[12]: ['', '', '', '', '', '', '', '', '', '', '', '', '', '', 'Eon']
  ROW[13]: ['100', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
  ROW[14]: ['', '', '', '', '', '', 'CRSS', '', '', '5', '', '', '', '', '']
  ROW[15]: ['10', '', '', '', '', '', '', '', '', '0', '', '', '', '', '']
  ROW[16]: ['', '0', '200', '400', '600', '800', '', '1000', '1200', '', '0', '40', '80', '120', '160']

## Page 6, Table 0 (flavor=stream, score=70.0)
  ROW[0]: ['', '', '', '', '', 'ASC300N1200ME3-X']
  ROW[1]: ['', '', '', '', '', '1200V, Half-Bridge, Silicon Carbide MOSFET Module']
  ROW[2]: ['T', 'ypical Performance', '', '', '', '']
  ROW[3]: ['', '', '0.1', '', '', '']
  ROW[4]: ['', 'Thermal Impedance, Zth(K/W)', '0.01', '', '', '']
  ROW[5]: ['', '', '0.001', '', '', '']
  ROW[6]: ['', '', '0.001', '0.01 0.1 1', '10', '']
  ROW[7]: ['', '', '', 'Time, t (s)', '', '']
  ROW[8]: ['', '', '', 'Figure 9', '', 'Figure 10']
  ROW[9]: ['', '', '', 'MOSFET Transient Thermal Impedance', '', 'Switching Time Description']
  ROW[10]: ['ASC300N1200ME3-X www.astsic.com', '', '', '', '', '']
  ROW[11]: ['Product Data Sheet 6 ASTC-3T03-202A A/0', '', '', '', '', '']

## Page 7, Table 0 (flavor=lattice, score=82.9)
  ROW[0]: ['未标注线性公差按 GB/1804-2000c 级执行', '公差分段', '0.5-3', '3-6', '6-30', '30-120', '120-400']
  ROW[1]: ['', 'c 级', '±0.2', '±0.3', '±0.5', '±0.8', '±1.2']

## Page 7, Table 1 (flavor=stream, score=70.0)
  ROW[0]: ['', '', '', '', '', '', 'ASC300N1200ME3-X']
  ROW[1]: ['', '', '', '', '1200V, Half-Bridge, Silicon Carbide MOSFET Module', '', '']
  ROW[2]: ['C ircuit Diagram Headline', '', '', '', '', '', '']
  ROW[3]: ['Package Dimensions (mm)', '', '', '', '', '', '']
  ROW[4]: ['', 'Package Type：ME3', '', '', '', '', '']
  ROW[5]: ['', '公差分段', '0.5-3', '3-6', '6-30', '30-120', '120-400']
  ROW[6]: ['未标注线性公差按', '', '', '', '', '', '']
  ROW[7]: ['GB/1804-2000c 级执行', '', '', '', '', '', '']
  ROW[8]: ['', 'c 级', '±0.2', '±0.3', '±0.5', '±0.8', '±1.2']
  ROW[9]: ['ASC300N1200ME3-X www.astsic.com', '', '', '', '', '', '']
  ROW[10]: ['Product Data Sheet 7 ASTC-3T03-202A A/0', '', '', '', '', '', '']

## Page 8, Table 0 (flavor=stream, score=70.0)
  ROW[0]: ['', '', '1200V, Half-Bridge, Silicon Carbide MOSFET Module']
  ROW[1]: ['N', 'otes & Disclaimer', '']
  ROW[2]: ['This document and the information contained herein are subject to change without notice. Any such change', '', '']
  ROW[3]: ['shall be evidenced by the publication of an updated version of this document by AST Technology. No', '', '']
  ROW[4]: ['communication from any employee or agent of AST Technology or any third party shall effect an amendment or', '', '']
  ROW[5]: ['modification of this document.', '', '']
  ROW[6]: ['W', '', 'ith respect to any examples, hints or any typical values stated herein and/or any information regarding the']
  ROW[7]: ['application of the product, AST Technology hereby disclaims any and all warranties and liabilities of any kind,', '', '']
  ROW[8]: ['including without limitation warranties of non-infringement of intellectual property rights of any third party.', '', '']
  ROW[9]: ['A', 'ny information given in this document is subject to customer’s compliance with its obligations stated in this', '']
  ROW[10]: ['document and any applicable legal requirements, norms and standards concerning customer’s products and any', '', '']
  ROW[11]: ['use of the product of AST Technology in customer’s applications.', '', '']
  ROW[12]: ['T', 'he data contained in this document is exclusively intended for technically trained staff. It is the responsibility of', '']
  ROW[13]: ['customer’s technical departments to evaluate the suitability of the product for the intended application and the', '', '']
  ROW[14]: ['completeness of the product information given in this document with respect to such application.', '', '']
  ROW[15]: ['E', 'xcept as otherwise explicitly approved by AST Technology', 'in a written document signed by authorized']
  ROW[16]: ['representatives, the products of AST Technology may not be used in any applications where a failure of the product', '', '']
  ROW[17]: ['or any consequences of the use thereof can reasonably be expected to result in personal injury.', '', '']

# TARGET FIELDS

- manufacturer: Manufacturer (aliases: manufacturer, brand, company, target_unit: )
- part_number: Part Number (aliases: part number, model, type, part #, model no., target_unit: )
- module_type: Module Type (aliases: module type, package, configuration, topology, target_unit: )
- voltage_rating: Voltage Rating (aliases: voltage, VDS, VDSs, breakdown voltage, collector-emitter voltage, target_unit: )
- current_rating: Current Rating (aliases: current, ID, IC, continuous current, rated current, target_unit: )
- rds_on_25c: RDS(on) @25°C (aliases: RDS(on), RDS(on)@25°C, RDS(on) typ, on-resistance, Ron, target_unit: )
- rds_on_150c: RDS(on) @150°C (aliases: RDS(on), RDS(on)@150°C, on-resistance, target_unit: )
- vgs_th: VGS(th) (aliases: Vth, VGS(th), gate threshold voltage, threshold voltage, target_unit: )
- ciss: Ciss (aliases: Ciss, input capacitance, C11, C12, target_unit: )
- coss: Coss (aliases: Coss, output capacitance, C22, C23, target_unit: )
- crss: Crss (aliases: Crss, reverse transfer capacitance, C12, C23, target_unit: )
- qg: QG (Total Gate Charge) (aliases: QG, Qg, total gate charge, gate charge, target_unit: )
- qgs: QGS (Gate-Source Charge) (aliases: Qgs, QGS, gate-source charge, target_unit: )
- qgd: QGD (Gate-Drain Charge) (aliases: Qgd, QGD, gate-drain charge, Miller charge, target_unit: )
- eon: Eon (Turn-On Energy) (aliases: Eon, EON, turn-on energy, switching energy on, target_unit: )
- eoff: Eoff (Turn-Off Energy) (aliases: Eoff, EOFF, turn-off energy, switching energy off, target_unit: )
- trr: trr (Reverse Recovery Time) (aliases: trr, trr, reverse recovery time, t_rr, target_unit: )
- qrr: QRR (Reverse Recovery Charge) (aliases: Qrr, QRR, reverse recovery charge, target_unit: )
- irrm: IRRM (Reverse Recovery Current) (aliases: IRRM, Irrm, peak reverse recovery current, target_unit: )
- err: Err (Reverse Recovery Energy) (aliases: Err, ERR, reverse recovery energy, target_unit: )
- rth_jc: Rth JC (Junction-to-Case) (aliases: Rth JC, Rth(j-c), thermal resistance junction-case, Rth, target_unit: )
- rth_jh: Rth JH (Junction-to-Heat sink) (aliases: Rth JH, Rth(j-h), thermal resistance junction-heatsink, target_unit: )
- junction_temperature: Junction Temperature (aliases: TJ, Tj, junction temp, operating temperature, target_unit: )
- lstray: Lstray (Stray Inductance) (aliases: Lstray, Lstray, stray inductance, commutation inductance, target_unit: )
- weight: Weight (aliases: weight, mass, kg, target_unit: )
- isol: Visol (Isolation Voltage) (aliases: Visol, isolation voltage, Viso, dielectric strength, isolation, target_unit: )
- clearance_tt: Clearance T-T (Terminal to Terminal) (aliases: clearance, clearance terminal, terminal clearance, target_unit: )
- clearance_tb: Clearance T-B (Terminal to Baseplate) (aliases: clearance, clearance baseplate, baseplate clearance, target_unit: )
- creepage_tt: Creepage T-T (Terminal to Terminal) (aliases: creepage, creepage terminal, terminal creepage, target_unit: )
- creepage_tb: Creepage T-B (Terminal to Baseplate) (aliases: creepage, creepage baseplate, baseplate creepage, target_unit: )

# YOUR TASK

Review each table and identify candidate rows for each target field.
For each target field, select the BEST candidate row (highest confidence).
Also list all review candidates (lower confidence but still possible).
Return STRICT JSON only:

```json
{
  "candidates": [
    {
      "field_id": "voltage_rating",
      "label": "Drain-Source Voltage",
      "target_unit": "V",
      "selected": { "source_page": 1, "table_index": 0, "row_index": 3, "confidence": 0.95, "match_type": "exact", ... },
      "review": [
        { "source_page": 2, "table_index": 1, "row_index": 5, "confidence": 0.8, ... }
      ]
    }
  ]
}
```