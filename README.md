# BNCTDoseEngine

Sample program written in MYP programming language for BNCT dose calculation, capable of computing neutron flux in water phantom.

---

## Overview

**BNCTDoseEngine** implements:

1. **MYP** — *Monte-Carlo Yield Physics* — a small domain-specific language designed for nuclear and radiation physics calculations.
2. A **BNCT (Boron Neutron Capture Therapy)** sample program (`examples/water_phantom.myp`) that computes:
   - Thermal neutron flux profile through a water phantom using exponential attenuation and diffusion theory.
   - Absorbed dose rate contributions from boron, hydrogen, and nitrogen reactions.
   - Biologically weighted (RBE/CBE) total dose rate and estimated irradiation time.

---

## Quick Start

```bash
python run_myp.py examples/water_phantom.myp
```

**Expected output (truncated):**

```
================================================================
  BNCT Dose Calculation — Water Phantom Neutron Flux
  MYP (Monte-Carlo Yield Physics) Language — Sample Program
================================================================

Phantom geometry:
  Width  : 20 cm   Height : 20 cm   Depth  : 30 cm

Water nuclear data (thermal, 0.025 eV):
  Sigma_a (absorption) : 0.022243 cm-1
  Sigma_t (total)      : 2.6885   cm-1
  Diffusion coeff D    : 0.123985 cm

Neutron Flux Profile along Beam Axis:
  z (cm)   |  Phi(z) (n/cm²/s)  |  Phi/Phi₀
  ---------+--------------------+-----------
   0        | 1000000000         | 1
   3        | 314195             | 0.000314
   …

Peak (weighted) dose rate : 0.0356 Gy/s  at depth 0 cm
Estimated irradiation time: 337 s  (for 12 Gy)
```

---

## Repository Structure

```
BNCTDoseEngine/
├── myp/                        # MYP language implementation
│   ├── __init__.py
│   ├── lexer.py                # Tokeniser
│   ├── parser.py               # Recursive-descent parser → AST
│   └── interpreter.py          # Tree-walking interpreter + built-ins
├── examples/
│   └── water_phantom.myp       # BNCT dose calculation sample program
├── tests/
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── test_interpreter.py     # Includes end-to-end sample test
└── run_myp.py                  # CLI entry point
```

---

## MYP Language Reference

### Comments

```
# This is a comment
```

### Variables and Constants

```
CONST PI = 3.14159      # immutable
VAR   x  = 5.0          # mutable
x = x + 1               # reassignment (VAR must be declared first)
```

### Print

```
PRINT "label:", value, "unit"   # space-separated; strings and numbers mixed
PRINT                           # blank line
```

### Arithmetic and Operators

| Operator | Meaning                  |
|----------|--------------------------|
| `+` `-` `*` `/` | basic arithmetic |
| `**` or `^` | exponentiation (right-associative) |
| `==` `!=` `<` `>` `<=` `>=` | comparison (return `true`/`false`) |
| `AND` `OR` `NOT` | logical operators |

### Control Flow

```
FOR i FROM 0 TO 10           # inclusive; step defaults to 1
    PRINT i
END FOR

FOR i FROM 0 TO 10 STEP 2   # custom step
    PRINT i
END FOR

IF x > 0 THEN
    PRINT "positive"
ELSE
    PRINT "non-positive"
END IF
```

### Functions

```
FUNCTION area(r)
    RETURN pi() * r ** 2
END FUNCTION

VAR a = area(5.0)
PRINT a
```

### Built-in Math Functions

| Function | Description |
|----------|-------------|
| `exp(x)` | eˣ |
| `sqrt(x)` | √x |
| `ln(x)` | natural log |
| `log10(x)` | log base 10 |
| `abs(x)` | absolute value |
| `sin(x)` `cos(x)` `tan(x)` | trigonometry (radians) |
| `floor(x)` `ceil(x)` `round(x)` | rounding |
| `min(a,b)` `max(a,b)` | extrema |
| `pi()` | π ≈ 3.14159… |

### Built-in Physics Functions

| Function | Description |
|----------|-------------|
| `number_density(rho, A, n)` | Atom number density N = ρ·Nₐ·n / A (atoms/cm³) |
| `macro_xsec(N, sigma_barn)` | Macroscopic cross-section Σ = N·σ (cm⁻¹) |
| `diffusion_coeff(Sigma_tr)` | D = 1 / (3·Σ_tr) (cm) |
| `attenuated_flux(phi0, Sigma_t, z)` | Φ(z) = Φ₀·exp(−Σ_t·z) (n/cm²/s) |
| `dose_rate_gy_s(phi, Sigma, Q_MeV, rho)` | Dose rate D' = Φ·Σ·Q / ρ (Gy/s) |

### Pre-loaded Physical Constants

| Constant | Value | Unit |
|----------|-------|------|
| `AVOGADRO` | 6.02214076 × 10²³ | mol⁻¹ |
| `NEUTRON_MASS` | 1.67492749804 × 10⁻²⁴ | g |
| `MEV_TO_JOULE` | 1.60218 × 10⁻¹³ | J/MeV |
| `EV_TO_JOULE` | 1.60218 × 10⁻¹⁹ | J/eV |
| `BARN_TO_CM2` | 1 × 10⁻²⁴ | cm²/barn |
| `SPEED_OF_LIGHT` | 2.99792458 × 10¹⁰ | cm/s |
| `PLANCK` | 6.62607015 × 10⁻³⁴ | J·s |

---

## Running Tests

```bash
python -m pytest tests/ -v
```

143 tests cover the lexer, parser, interpreter, built-in functions, and the full BNCT sample program.

---

## Physics Background

**BNCT** selectively destroys cancer cells by:
1. Accumulating ¹⁰B in tumour tissue (via BPA or BSH compounds).
2. Irradiating with an epithermal neutron beam that thermalises inside the tissue.
3. The ¹⁰B(n,α)⁷Li reaction deposits high-LET radiation (~9 µm range) inside boron-loaded cells.

The sample program uses a **one-group diffusion / exponential attenuation model**:

```
Φ(z) = Φ₀ · exp(−Σ_t · z)
```

Dose components computed:

| Component | Reaction | CBE factor |
|-----------|----------|------------|
| Boron | ¹⁰B(n,α)⁷Li | 3.8 |
| Hydrogen | ¹H(n,γ)²H | 3.2 |
| Nitrogen | ¹⁴N(n,p)¹⁴C | 1.7 |

Total biologically weighted dose: `D_total = Σ CBEᵢ · Dᵢ`

---

## References

- Barth et al., *Radiation Oncology* **7**:146 (2012).
- Attix, *Introduction to Radiological Physics and Radiation Dosimetry*, Wiley-VCH (2004).
- ENDF/B-VIII.0 nuclear data library.
