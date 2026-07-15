# Backend Comparison Report
**PDF**: ASC300N1200ME3.pdf

## Camelot Availability
- Camelot available: **Yes**

- Lattice tables: **8**
- Stream tables: **13**

## pdfplumber
- Total tables: **35**

## Camelot Table Details
| # | Page | Flavor | Shape | Accuracy | Whitespace | Score | Preview |
|---|------|--------|-------|----------|------------|-------|--------|
| 0 | 1 | lattice | 3x2 | 100.0 | 0.0 | 85.0 | Order Number | ASC300N1200ME3-X<br>Marking | ASC300N1200ME3 |
| 1 | 1 | lattice | 14x7 | 96.3 | 40.8 | 105.0 | Symbol | Parameter | Values |  |  | Unit | Test Conditions<br>Absolute maximum rat |  |  |  |  |  |  |
| 2 | 1 | stream | 21x8 | 92.9 | 63.7 | 100.0 | Key Parameters |  |  |  |  |  |  | <br>Symbol | Parameter |  | Values |  | Unit |  | Test Conditions |
| 3 | 2 | lattice | 9x4 | 100.0 | 5.6 | 104.4 | Symbol | Parameter | Values | Unit<br>VDS | Drain-Source Voltage | 1200 | V |
| 4 | 2 | lattice | 23x7 | 99.5 | 18.0 | 112.0 | Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions<br>Static characteristi |  |  |  |  |  |  |
| 5 | 2 | stream | 11x4 | 98.8 | 20.4 | 95.0 |  | bsolute Maximum Rati |  | <br>Symbol | Parameter | Values | Unit |
| 6 | 2 | stream | 10x6 | 100.0 | 28.3 | 75.0 | Eon | Turn-on Energy | - | 7.1 | - | <br> |  |  |  |  | mJ |
| 7 | 2 | stream | 31x7 | 98.7 | 38.2 | 110.0 | Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions<br>Static characteristi |  |  |  |  |  |  |
| 8 | 3 | lattice | 6x7 | 100.0 | 4.8 | 125.2 | Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions<br>VFSD | Forward Voltage | - | 3.5 | 6 | V | VGS=0V; IF=150A |
| 9 | 3 | lattice | 9x7 | 100.0 | 11.1 | 118.9 | Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions<br>LStray | Stray Inductance | - | 20 | - | nH |  |
| 10 | 3 | stream | 9x8 | 97.5 | 40.3 | 110.0 | B | ody Diode Characteri |  |  |  |  |  | <br> | Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| 11 | 3 | stream | 12x7 | 98.8 | 32.1 | 110.0 | Module Physical Char |  |  |  |  |  | <br>Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| 12 | 4 | stream | 18x6 | 100.0 | 78.7 | 70.0 |  | 600 |  |  |  | 2<br> |  | VGS=20V | VGS=18V |  |  |
| 13 | 4 | stream | 16x7 | 100.0 | 83.0 | 70.0 |  | 3.5 |  | 600 |  |  | <br> |  |  |  | VDS=20V |  |  |
| 14 | 5 | lattice | 7x7 | 82.8 | 81.6 | 70.0 | 25 20 15 10 Switchin |  |  |  |  |  | <br> | VGS=-5/+18V VDS=800V |  |  |  |  |  |
| 15 | 5 | stream | 19x15 | 94.2 | 89.1 | 70.0 |  |  |  |  |  |  |  |  | 20 |  |  |  |  |  | <br>-5 | -4 | -3 | -2 | -1 | 0 |  |  |  |  |  |  |  |  |  |
| 16 | 5 | stream | 17x15 | 100.0 | 86.3 | 70.0 | 100000 |  |  |  |  |  |  |  |  | 25 |  |  |  |  | <br> |  |  |  |  |  |  |  |  |  |  | VGS=-5/+18V |  |  |  |
| 17 | 6 | stream | 12x6 | 87.4 | 75.0 | 70.0 |  |  |  |  |  | ASC300N1200ME3-X<br> |  |  |  |  | 1200V, Half-Bridge,  |
| 18 | 7 | lattice | 2x7 | 100.0 | 7.1 | 82.9 | 未标注线性公差按 GB/1804-200 | 公差分段 | 0.5-3 | 3-6 | 6-30 | 30-120 | 120-400<br> | c 级 | ±0.2 | ±0.3 | ±0.5 | ±0.8 | ±1.2 |
| 19 | 7 | stream | 11x7 | 90.1 | 72.7 | 70.0 |  |  |  |  |  |  | ASC300N1200ME3-X<br> |  |  |  | 1200V, Half-Bridge,  |  |  |
| 20 | 8 | stream | 18x3 | 44.0 | 55.6 | 70.0 |  |  | 1200V, Half-Bridge, <br>N | otes & Disclaimer |  |

## Likely Parameter Tables
Candidate tables (score >= 50): **21**

### Table 1 (score=125.2)
- Page: 3, Flavor: lattice
- Shape: 6x7
- Accuracy: 100.0, Whitespace: 4.76

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| VFSD | Forward Voltage | - | 3.5 | 6 | V | VGS=0V; IF=150A |
| IS | Continuous Diode Forward Current | - | 150 | - | A | VGS=0V; TC=25C |
| tRR | Reverse Recovery Time | - | 96 | - | ns | VGS=-5/+18V; IF=150A; VR=800V; RG(ext)=5Ω; Load=50µH |
| QRR | Reverse Recovery Charge | - | 1839 | - | nC |  |
```

### Table 2 (score=118.9)
- Page: 3, Flavor: lattice
- Shape: 9x7
- Accuracy: 100.0, Whitespace: 11.11

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| LStray | Stray Inductance | - | 20 | - | nH |  |
| W | Weight | - | 340 | - | g |  |
| Ms | Mounting Torque | 4.0 | - | 5.5 | Nm | M6-1.0 Bolts |
| Visol | Case Isolation Voltage (DC; t=1min) | 4.2 | - | - | kV |  |
```

### Table 3 (score=112.0)
- Page: 2, Flavor: lattice
- Shape: 23x7
- Accuracy: 99.45, Whitespace: 18.01

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| Static characteristics (at TC=25℃ unless otherwise specified) |  |  |  |  |  |  |
| BVDS | Drain-Source Breakdown Voltage | 1200 | - | - | V | VGS=0V |
| IDSS | Zero Gate Voltage Drain Current | - | - | 150 | μA | VDS=1200V; VGS=0V |
| IGSS | Gate-Body Leakage Current | - | - | 1.5 | μA | VGS=-10/20V; VDS=0V |
```

### Table 4 (score=110.0)
- Page: 2, Flavor: stream
- Shape: 31x7
- Accuracy: 98.74, Whitespace: 38.25

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| Static characteristics (at TC=25℃ unless otherwise specified) |  |  |  |  |  |  |
| BVDS | Drain-Source Breakdown Voltage | 1200 | - | - | V | VGS=0V |
| IDSS | Zero Gate Voltage Drain Current | - | - | 150 | μA | VDS=1200V; VGS=0V |
| IGSS | Gate-Body Leakage Current | - | - | 1.5 | μA | VGS=-10/20V; VDS=0V |
```

### Table 5 (score=110.0)
- Page: 3, Flavor: stream
- Shape: 9x8
- Accuracy: 97.55, Whitespace: 40.28

**Preview (first 5 rows):**

```
| B | ody Diode Characteristics (at TJ=25℃ unless otherwise specified) |  |  |  |  |  |  |
|  | Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
|  | VFSD | Forward Voltage | - | 3.5 | 6 | V | VGS=0V; IF=150A |
|  | IS | Continuous Diode Forward Current | - | 150 | - | A | VGS=0V; TC=25C |
|  | tRR | Reverse Recovery Time | - | 96 | - | ns |  |
```

### Table 6 (score=110.0)
- Page: 3, Flavor: stream
- Shape: 12x7
- Accuracy: 98.75, Whitespace: 32.14

**Preview (first 5 rows):**

```
| Module Physical Characteristics |  |  |  |  |  |  |
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| LStray | Stray Inductance | - | 20 | - | nH |  |
| W | Weight | - | 340 | - | g |  |
| Ms | Mounting Torque | 4.0 | - | 5.5 | Nm | M6-1.0 Bolts |
```

### Table 7 (score=105.0)
- Page: 1, Flavor: lattice
- Shape: 14x7
- Accuracy: 96.35, Whitespace: 40.82

**Preview (first 5 rows):**

```
| Symbol | Parameter | Values |  |  | Unit | Test Conditions |
| Absolute maximum rating |  |  |  |  |  |  |
| VDS | Drain-Source Voltage | 1200 |  |  | V | TC=25C |
| ID | Drain Current (continuous) | 300 |  |  | A | TC=25C |
|  |  | 240 |  |  |  | TC=75C |
```

### Table 8 (score=104.4)
- Page: 2, Flavor: lattice
- Shape: 9x4
- Accuracy: 100.0, Whitespace: 5.56

**Preview (first 5 rows):**

```
| Symbol | Parameter | Values | Unit |
| VDS | Drain-Source Voltage | 1200 | V |
| VGS | Gate-Source Voltage (dynamic) | -10/+22 | V |
| ID | Drain Current (continuous; TC=25C) | 300 | A |
|  | Drain Current (continuous; TC=75C) | 240 |  |
```

### Table 9 (score=100.0)
- Page: 1, Flavor: stream
- Shape: 21x8
- Accuracy: 92.94, Whitespace: 63.69

**Preview (first 5 rows):**

```
| Key Parameters |  |  |  |  |  |  |  |
| Symbol | Parameter |  | Values |  | Unit |  | Test Conditions |
| Absolute maximum rating |  |  |  |  |  |  |  |
| VDS | Drain-Source Voltage |  | 1200 |  | V | TC=25C |  |
|  |  |  | 300 |  |  | TC=25C |  |
```

### Table 10 (score=95.0)
- Page: 2, Flavor: stream
- Shape: 11x4
- Accuracy: 98.8, Whitespace: 20.45

**Preview (first 5 rows):**

```
|  | bsolute Maximum Ratings (at TC=25℃ unless otherwise specified) |  |  |
| Symbol | Parameter | Values | Unit |
| VDS | Drain-Source Voltage | 1200 | V |
| VGS | Gate-Source Voltage (dynamic) | -10/+22 | V |
|  | Drain Current (continuous; TC=25C) | 300 |  |
```

### Table 11 (score=85.0)
- Page: 1, Flavor: lattice
- Shape: 3x2
- Accuracy: 100.0, Whitespace: 0.0

**Preview (first 5 rows):**

```
| Order Number | ASC300N1200ME3-X |
| Marking | ASC300N1200ME3 |
| Package Type | ME3 |
```

### Table 12 (score=82.9)
- Page: 7, Flavor: lattice
- Shape: 2x7
- Accuracy: 100.0, Whitespace: 7.14

**Preview (first 5 rows):**

```
| 未标注线性公差按 GB/1804-2000c 级执行 | 公差分段 | 0.5-3 | 3-6 | 6-30 | 30-120 | 120-400 |
|  | c 级 | ±0.2 | ±0.3 | ±0.5 | ±0.8 | ±1.2 |
```

### Table 13 (score=75.0)
- Page: 2, Flavor: stream
- Shape: 10x6
- Accuracy: 100.0, Whitespace: 28.33

**Preview (first 5 rows):**

```
| Eon | Turn-on Energy | - | 7.1 | - |  |
|  |  |  |  |  | mJ |
| Eoff | Turn-off Energy | - | 7.9 | - |  |
| QGS | Gate-Source Charge | - | 174 | - |  |
| QGD | Gate-Drain Charge | - | 147 | - | nC |
```

### Table 14 (score=70.0)
- Page: 4, Flavor: stream
- Shape: 18x6
- Accuracy: 100.0, Whitespace: 78.7

**Preview (first 5 rows):**

```
|  | 600 |  |  |  | 2 |
|  |  | VGS=20V | VGS=18V |  |  |
|  |  |  |  |  | 1.8 |
|  | 500 |  |  |  |  |
|  |  |  |  |  | 1.6 |
```

### Table 15 (score=70.0)
- Page: 4, Flavor: stream
- Shape: 16x7
- Accuracy: 100.0, Whitespace: 83.04

**Preview (first 5 rows):**

```
|  | 3.5 |  | 600 |  |  |  |
|  |  |  |  | VDS=20V |  |  |
|  | 3 |  |  |  |  |  |
|  |  |  | 500 |  |  |  |
|  | 2.5 |  |  |  |  |  |
```

### Table 16 (score=70.0)
- Page: 5, Flavor: lattice
- Shape: 7x7
- Accuracy: 82.84, Whitespace: 81.63

**Preview (first 5 rows):**

```
| 25 20 15 10 Switching Loss (mJ) 5 0 0 40 |  |  |  |  |  |  |
|  | VGS=-5/+18V VDS=800V L=100μH |  |  |  |  |  |
|  | RG(ext)=5Ω |  |  |  | Etotal |  |
|  |  |  |  |  | Eoff |  |
|  |  |  |  |  | Eon |  |
```

### Table 17 (score=70.0)
- Page: 5, Flavor: stream
- Shape: 19x15
- Accuracy: 94.22, Whitespace: 89.12

**Preview (first 5 rows):**

```
|  |  |  |  |  |  |  |  | 20 |  |  |  |  |  |  |
| -5 | -4 | -3 | -2 | -1 | 0 |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  | 0 |  |  |  |  |  |  |  |  |
| VGS=-5V |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  | 15 |  |  |  |  |  |  |
```

### Table 18 (score=70.0)
- Page: 5, Flavor: stream
- Shape: 17x15
- Accuracy: 100.0, Whitespace: 86.27

**Preview (first 5 rows):**

```
| 100000 |  |  |  |  |  |  |  |  | 25 |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  | VGS=-5/+18V |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  | VDS=800V |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  | L=100μH |  |  |  |
|  |  |  |  |  |  |  |  |  | 20 |  | RG(ext)=5Ω |  |  |  |
```

### Table 19 (score=70.0)
- Page: 6, Flavor: stream
- Shape: 12x6
- Accuracy: 87.4, Whitespace: 75.0

**Preview (first 5 rows):**

```
|  |  |  |  |  | ASC300N1200ME3-X |
|  |  |  |  |  | 1200V, Half-Bridge, Silicon Carbide MOSFET Module |
| T | ypical Performance |  |  |  |  |
|  |  | 0.1 |  |  |  |
|  | Thermal Impedance, Zth(K/W) | 0.01 |  |  |  |
```

### Table 20 (score=70.0)
- Page: 7, Flavor: stream
- Shape: 11x7
- Accuracy: 90.09, Whitespace: 72.73

**Preview (first 5 rows):**

```
|  |  |  |  |  |  | ASC300N1200ME3-X |
|  |  |  |  | 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |  |
| C ircuit Diagram Headline |  |  |  |  |  |  |
| Package Dimensions (mm) |  |  |  |  |  |  |
|  | Package Type：ME3 |  |  |  |  |  |
```

### Table 21 (score=70.0)
- Page: 8, Flavor: stream
- Shape: 18x3
- Accuracy: 44.04, Whitespace: 55.56

**Preview (first 5 rows):**

```
|  |  | 1200V, Half-Bridge, Silicon Carbide MOSFET Module |
| N | otes & Disclaimer |  |
| This document and the information contained herein are subject to change without notice. Any such change |  |  |
| shall be evidenced by the publication of an updated version of this document by AST Technology. No |  |  |
| communication from any employee or agent of AST Technology or any third party shall effect an amendment or |  |  |
```

## Manual Inspection Needed
Tables needing review (30 <= score < 50): **0**


## pdfplumber Tables
### Table 1
- Page: 1, Shape: 0x0

**Preview (first 5 rows):**

```
```

### Table 2
- Page: 1, Shape: 3x2

**Preview (first 5 rows):**

```
| Order Number | ASC300N1200ME3-X |
| Marking | ASC300N1200ME3 |
| Package Type | ME3 |
```

### Table 3
- Page: 1, Shape: 14x7

**Preview (first 5 rows):**

```
| Symbol | Parameter | Values |  |  | Unit | Test Conditions |
| Absolute maximum rating |  |  |  |  |  |  |
| V DS | Drain-Source Voltage | 1200 |  |  | V | T =25C C |
| I D | Drain Current (continuous) | 300 |  |  | A | T =25C C |
|  |  | 240 |  |  |  | T =75C C |
```

### Table 4
- Page: 2, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

### Table 5
- Page: 2, Shape: 9x4

**Preview (first 5 rows):**

```
| Symbol | Parameter | Values | Unit |
| V DS | Drain-Source Voltage | 1200 | V |
| V GS | Gate-Source Voltage (dynamic) | -10/+22 | V |
| I D | Drain Current (continuous; T =25C) C | 300 | A |
|  | Drain Current (continuous; T =75C) C | 240 |  |
```

### Table 6
- Page: 2, Shape: 23x7

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| Static characteristics (at T =25℃ unless otherwise specified) C |  |  |  |  |  |  |
| BV DS | Drain-Source Breakdown Voltage | 1200 | - | - | V | V =0V GS |
| I DSS | Zero Gate Voltage Drain Current | - | - | 150 | μA | V =1200V; V =0V DS GS |
| I GSS | Gate-Body Leakage Current | - | - | 1.5 | μA | V =-10/20V; V =0V GS DS |
```

### Table 7
- Page: 3, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

### Table 8
- Page: 3, Shape: 6x7

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| V FSD | Forward Voltage | - | 3.5 | 6 | V | V =0V; I =150A GS F |
| I S | Continuous Diode Forward Current | - | 150 | - | A | V =0V; T =25C GS C |
| t RR | Reverse Recovery Time | - | 96 | - | ns | V =-5/+18V; I =150A; V =800V; GS F R R =5Ω; Load=50µH G(ext) |
| Q RR | Reverse Recovery Charge | - | 1839 | - | nC |  |
```

### Table 9
- Page: 3, Shape: 9x7

**Preview (first 5 rows):**

```
| Symbol | Parameter | Min. | Typ. | Max. | Unit | Test Conditions |
| L Stray | Stray Inductance | - | 20 | - | nH |  |
| W | Weight | - | 340 | - | g |  |
| M s | Mounting Torque | 4.0 | - | 5.5 | Nm | M6-1.0 Bolts |
| V isol | Case Isolation Voltage (DC; t=1min) | 4.2 | - | - | kV |  |
```

### Table 10
- Page: 4, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

### Table 11
- Page: 4, Shape: 2x1

**Preview (first 5 rows):**

```
| 600 V GS =20V V GS =18V 500 )A V =16V ( 400 GS SD I ,tn e rru 300 C e c ru V GS =12V o S - 200 n ia rD 100 V =8V GS 0 0 2 4 6 8 Drain-Source Voltage, V (V) DS |
| Figure 1 Output Characteristics (T=25C) J |
```

### Table 12
- Page: 4, Shape: 2x1

**Preview (first 5 rows):**

```
| 2 1.8 1.6 1.4 )no(SD 1.2 R ,e 1 c n a ts ise 0.8 R n O 0.6 0.4 0.2 0 -50 -25 0 25 50 75 100 125 150 175 Junction Temperature, T (°C) J |
| Figure 2 Normalized On-Resistance vs. Temperature |
```

### Table 13
- Page: 4, Shape: 4x4

**Preview (first 5 rows):**

```
| V GS | =20V V = GS | 18V |  |
|  | V = GS | 16V |  |
|  | V = GS | 12V |  |
|  | V = GS | 8V |  |
```

### Table 14
- Page: 4, Shape: 0x0

**Preview (first 5 rows):**

```
```

### Table 15
- Page: 4, Shape: 2x1

**Preview (first 5 rows):**

```
| 3.5 3 2.5 )V ( ht V ,e 2 g a tlo V d 1.5 lo h se rh T 1 0.5 0 -50 -25 0 25 50 75 100 125 150 175 Junction Temperature, T (°C) J |
| Figure 3 Threshold Voltage vs. Temperature |
```

### Table 16
- Page: 4, Shape: 2x1

**Preview (first 5 rows):**

```
| 600 V =20V DS 500 )A 400 ( SD I ,tn e T=175℃ rru 300 J C e c ru T J =25℃ o S 200 - n ia T=-55℃ rD J 100 0 0 2 4 6 8 10 12 Gate-Source Voltage, V (V) GS |
| Figure 4 Transfer Characteristic for Various T; V =20V J DS |
```

### Table 17
- Page: 4, Shape: 0x0

**Preview (first 5 rows):**

```
```

### Table 18
- Page: 4, Shape: 4x6

**Preview (first 5 rows):**

```
| V =20V DS |  |  |  |  |  |
|  |  | T= J | 175℃ |  |  |
|  |  |  | T=25 J | ℃ |  |
|  |  |  |  | T=-5 J | 5℃ |
```

### Table 19
- Page: 5, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

### Table 20
- Page: 5, Shape: 2x1

**Preview (first 5 rows):**

```
| -10 -9 -8 -7 -6 -5 -4 -3 -2 -1 0 0 V =-5V GS -100 V =-2V GS )A ( SD -200 I ,tn V =0V GS e rru C -300 e c ru o S n - -400 ia rD -500 -600 Drain-Source Voltage, V (V) DS |
| Figure 5 Diode Characteristic at 25˚C |
```

### Table 21
- Page: 5, Shape: 3x2

**Preview (first 5 rows):**

```
| 20 15 )V ( SG V 10 ,e g a tlo V e c 5 ru o S - e ta G 0 -5 0 150 300 450 600 750 Gate Charge, Q (nC) G |  |
|  | 20 15 )V ( SG V 10 ,e g a tlo V e c 5 ru o S - e ta G 0 -5 0 150 300 450 600 750 Gate Charge, Q (nC) G |
| Figure 6 Typical Gate Charge Characteristics |  |
```

### Table 22
- Page: 5, Shape: 0x0

**Preview (first 5 rows):**

```
```

### Table 23
- Page: 5, Shape: 3x10

**Preview (first 5 rows):**

```
|  |  |  |  | V = GS | -5V |  |  |  |  |
|  |  |  |  | V | =-2 GS | V |  |  |  |
|  |  |  |  |  |  | V =0 GS | V |  |  |
```

### Table 24
- Page: 5, Shape: 2x1

**Preview (first 5 rows):**

```
| 100000 C 10000 ISS )F p ( e1000 c n a tic C a OSS p a C 100 C RSS 10 0 200 400 600 800 1000 1200 Drain-Source Voltage, V (V) DS |
| Figure 7 Typical Capacitances vs. Drain-Source Voltage |
```

### Table 25
- Page: 5, Shape: 2x1

**Preview (first 5 rows):**

```
| 25 V =-5/+18V GS V =800V DS L=100μH 20 R G(ext) =5Ω E total )Jm 15 ( s so L g E off n ih 10 c tiw S E on 5 0 0 40 80 120 160 200 Drain-Source Current, I (A) DS |
| Figure 8 Inductive Switching Energy vs. Drain Current |
```

### Table 26
- Page: 5, Shape: 4x30

**Preview (first 5 rows):**

```
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | C | ISS |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | C |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | OSS |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | C | RSS |  |  |  |  |  |  |  |
```

### Table 27
- Page: 5, Shape: 4x6

**Preview (first 5 rows):**

```
| V =-5/+1 GS V =800V DS L=100μH R =5Ω | 8V |  |  |  |  |
| G(ext) |  |  |  |  | E total |
|  |  |  |  |  | E off |
|  |  |  |  |  | E on |
```

### Table 28
- Page: 6, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

### Table 29
- Page: 6, Shape: 2x1

**Preview (first 5 rows):**

```
| 0.1 )W /K ( ht Z ,e c n a d e p 0.01 m I la m re h T 0.001 0.001 0.01 0.1 1 10 Time, t (s) |
| Figure 9 MOSFET Transient Thermal Impedance |
```

### Table 30
- Page: 6, Shape: 1x1

**Preview (first 5 rows):**

```
| Figure 10 Switching Time Description |
```

### Table 31
- Page: 6, Shape: 0x0

**Preview (first 5 rows):**

```
```

### Table 32
- Page: 7, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

### Table 33
- Page: 7, Shape: 2x7

**Preview (first 5 rows):**

```
| 未标注线性公差按 GB/1804-2000c级执行 | 公差分段 | 0.5-3 | 3-6 | 6-30 | 30-120 | 120-400 |
|  | c级 | ±0.2 | ±0.3 | ±0.5 | ±0.8 | ±1.2 |
```

### Table 34
- Page: 7, Shape: 2x1

**Preview (first 5 rows):**

```
| 未标注线性公差按 |
| GB/1804-2000c级执行 |
```

### Table 35
- Page: 8, Shape: 2x2

**Preview (first 5 rows):**

```
|  | ASC300N1200ME3-X |
| 1200V, Half-Bridge, Silicon Carbide MOSFET Module |  |
```

## Recommendations
- **21 table(s)** scored high enough to likely be parameter tables.
- Camelot is recommended for text-based PDFs; try `--backend camelot`.
- Lattice found 8 table(s), stream found 13 table(s).
- Stream flavor performed better for this PDF.
