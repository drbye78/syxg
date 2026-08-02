# Waveguide Instruments Reference

Seven Numba-JIT digital waveguide instruments for physically-inspired synthesis.

## Bowed String (Violin, Cello, Viola)

```
BowedStringWaveguide(sample_rate=44100)
Params: bow_velocity (0-1), bow_pressure (0-1), bow_position (0-1)
        position=0 → sul ponticello (bright); position=1 → sul tasto (dark)
Physics: Karplus-Strong delay line with stick-slip friction model
```

## Brass (Trumpet, Trombone, Horn)

```
BrassWaveguide(sample_rate=44100)
Params: mouth_pressure (0-1), lip_tension (0-1)
        Higher tension → tighter embouchure → higher resonant frequency
Physics: Lip mass-spring oscillator + conical bore waveguide
```

## Clarinet

```
ClarinetWaveguide(sample_rate=44100)
Params: mouth_pressure (0-1), lip_tension (0-1)
        Lower tension → softer reed → easier to play
Physics: Single-reed nonlinear oscillator + cylindrical bore (odd overtones)
```

## Saxophone

```
SaxophoneWaveguide(sample_rate=44100)
Reuses clarinet_block with conical bore geometry.
Params: mouth_pressure (0-1), lip_tension (0-1)
Physics: Single-reed + conical bore (even + odd overtones)
```

## Oboe

```
OboeWaveguide(sample_rate=44100)
Params: mouth_pressure (0-1), reed_stiffness (0-1)
        Higher stiffness → harder reed → brighter tone
Physics: Double-reed nonlinear oscillator + conical bore
```

## Flute

```
FluteWaveguide(sample_rate=44100)
Params: air_pressure (0-1), embouchure_distance (0-1)
        Further edge → more stable jet → purer tone
Physics: Air jet edge-tone + inline LCG turbulence model
```

## Recorder

```
RecorderWaveguide(sample_rate=44100)
Params: air_pressure (0-1)
        Lower pressure than flute (0.3 default vs 0.4)
Physics: Fipple edge — deterministic (no turbulence). Purer, softer tone
```
