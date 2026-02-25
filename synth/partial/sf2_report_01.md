### Overview

The SF2 engine/region/partial stack is clearly aiming for a very ambitious, spec‑heavy SF2 implementation, but a lot of the “production‑grade” behavior in docstrings is not actually wired up correctly. There are several concrete runtime bugs and structural issues that will break or severely limit actual audio output.

Below are the main, **code‑level** problems in the synthesis pipeline.

---

### 1. `SF2Partial` is currently not constructible (broken `__slots__`)

`SF2Partial` defines `__slots__`:

```18:52:synth/partial/sf2_partial.py
class SF2Partial(SynthesisPartial):
    __slots__ = [
        'synth', 'sample_data', 'phase_step', 'sample_position', 'pitch_ratio',
        'loop_mode', 'loop_start', 'loop_end', 'envelope', 'filter',
        'mod_lfo', 'vib_lfo', 'audio_buffer', 'work_buffer',
        'pitch_mod', 'filter_mod', 'volume_mod', 'active', 'params',
        ...
        'overriding_root_key', 'scale_tuning',
        # Volume Envelope (missing hold)
        'hold_vol_env'
    ]
```

But in `__init__` it assigns many attributes **not** in `__slots__`, for example:

```79:87:synth/partial/sf2_partial.py
self.vib_lfo_buffer = None
self.mod_lfo_buffer = None
self.mod_env_buffer = None
self.lfo_pitch_buffer = None
self.lfo_filter_buffer = None
self.lfo_volume_buffer = None
self.lfo_pan_buffer = None

self._pitch_mod_vector = None
...
self._buffers_allocated = False
```

Because `__slots__` is present and does not include those names, any such assignment will raise `AttributeError` at runtime. So **constructing `SF2Partial` will fail** before any audio is generated.

Similar issues exist throughout the class (`_mod_env_state`, `_vib_lfo_phase`, `_mod_lfo_phase`, `_channel_pan`, etc. are used but not declared in `__slots__`).

**Impact:** The SF2 audio path via `SF2Partial` is effectively non‑functional until `__slots__` is fixed to include all attributes or removed.

---

### 2. `SF2Region` → `SF2Partial` integration uses the wrong constructor signature

`SF2Partial.__init__` is:

```55:66:synth/partial/sf2_partial.py
def __init__(self, params: Dict, synth: 'ModernXGSynthesizer'):
    super().__init__(params, synth.sample_rate)
    self.synth = synth
```

But `SF2Region._create_partial` does:

```250:259:synth/partial/sf2_region.py
from ..partial.sf2_partial import SF2Partial
...
partial = SF2Partial(partial_params, self.sample_rate)
```

It passes `sample_rate` (an `int`) where a `ModernXGSynthesizer` instance is required. That will fail immediately (e.g., `synth.sample_rate` access in `SF2Partial.__init__` will blow up).

**Impact:** The region‑based SF2 path cannot create partials successfully.

---

### 3. `SF2Engine` generate path doesn’t actually use SF2 data

`SF2Engine.generate_samples`:

```797:819:synth/engine/sf2_engine.py
partial_params = self.get_default_partial_params()
partial_params['note'] = note
partial_params['velocity'] = velocity

partial = self.create_partial(partial_params, self.sample_rate)
partial.note_on(velocity, note)

return partial.generate_samples(block_size, modulation)
```

Issues:

- It **does not look up any SF2 preset/zone** or sample. It just uses default params.
- `create_partial` tries to fetch `sample_data` from the soundfont manager using `sample_index` / `sample_id` in `partial_params`, but `generate_samples` does not set those, so `sample_data` remains absent.
- In `SF2Partial._load_sf2_parameters`, sample data is taken from `self.params.get('sample_data')`; if it’s missing, `self.sample_data` stays `None`.
- `generate_samples` in `SF2Partial` early‑outs to silence if `self.sample_data` is `None`:

```269:270:synth/partial/sf2_partial.py
if not self.active or self.sample_data is None:
    return np.zeros(block_size * 2, dtype=np.float32)
```

**Impact:** `SF2Engine.generate_samples` as written will generally return silence unless some external caller pre‑populates `sample_data` in `partial_params`. It does not connect MIDI/program/bank to SF2 presets at all.

---

### 4. `SF2Region` depends on manager methods that don’t exist

`SF2Region` expects the `SF2SoundFontManager` to have:

- `get_sample_loop_info(sample_id)`
- `get_sample_info(sample_id)`
- `get_zone(region_id)`

e.g.:

```136:140:synth/partial/sf2_region.py
loop_info = self.soundfont_manager.get_sample_loop_info(self.descriptor.sample_id)
...
sample_info = self.soundfont_manager.get_sample_info(self.descriptor.sample_id)
...
self._sf2_zone = self.soundfont_manager.get_zone(self.descriptor.region_id)
```

But `SF2SoundFontManager` (in `synth/sf2/sf2_soundfont_manager.py`) **does not implement any of these methods**. So:

- Loop points (`_loop_start`, `_loop_end`, `_loop_mode`) are never correctly populated.
- Root key/tuning via `get_sample_info` are never populated.
- The zone object used to populate `_generator_params`, `_modulators`, `_key_range`, etc. is never obtained.

**Impact:** The region’s “SF2‑aware” behavior (loops, tuning, generator inheritance, key/velocity ranges) is dead code right now, and the calls will raise `AttributeError` if executed.

---

### 5. Region → partial parameter mapping is inconsistent

`SF2Region._build_partial_params_from_generators` builds a flat dict with keys like:

```270:363:synth/partial/sf2_region.py
params = {
    'sample_data': self._sample_data,
    'note': self.current_note,
    'velocity': self.current_velocity,
    'original_pitch': self._root_key,
    'loop': {...}
}
params['amp_delay'] = ...
params['amp_attack'] = ...
...
params['filter_cutoff'] = ...
...
params['reverb_send'] = ...
...
params['coarse_tune'] = ...
...
params['scale_tuning'] = ...
```

But `SF2Partial._load_sf2_parameters` expects parameters grouped differently:

- Sample data under `'sample_data'` (ok),
- Loop info under `'loop'` (ok),
- Envelope under `'amp_envelope'` dict (not present),
- Filter under `'filter'` dict with keys `cutoff`, `resonance`, `type`, etc.,
- LFOs under `'mod_lfo'`, `'vib_lfo'` dicts, etc.

So even if you fix the constructor mismatch and manager methods, the partial will ignore most of these unstructured keys and fall back to its own defaults.

**Impact:** Actual SF2 generator values (attack/decay/sustain, filter cutoff/Q, etc.) are not correctly transferred into the partial, so the sound will not follow the SF2 file’s programming.

---

### 6. Wrong generator IDs and semantics inside `SF2Partial`

`_load_sf2_generator_values` maps SF2 generator IDs to internal fields, but many IDs are wrong per the SF2 spec. Examples:

```1704:1712:synth/partial/sf2_partial.py
self.chorus_effects_send = self._convert_sf2_generator(15, generators.get(15, 0)) / 1000.0
self.reverb_effects_send = self._convert_sf2_generator(16, generators.get(16, 0)) / 1000.0

self.key_range = self._parse_key_range(generators.get(43, 0))
self.vel_range = self._parse_vel_range(generators.get(44, 0))
self.exclusive_class = generators.get(57, 0)
self.sample_modes = generators.get(54, 0)
```

But in `sf2_constants.SF2_GENERATORS`, the mappings are:

- Chorus send is generator **33**, reverb send is **32**.
- Key range is generator **42**, vel range is **43** (your constants file itself inconsistently lists 42/43/62/63).
- Sample modes is generator **51**, exclusive class is **53**.

Later:

```1729:1735
self.mod_env_to_pitch = generators.get(7, 0) / 100.0
...
self.delay_mod_env = self._convert_time_cent(25, generators.get(25, -12000))
...
# etc.
```

But in the spec:

- `modEnvToPitch` is generator **20**, not 7.
- 25–30 are LFO parameters / sample modes, not mod‑env times.

**Impact:** Even if everything else worked, the actual synthesizer parameters derived from SF2 generators would be **nonsensical**, leading to wrong envelopes, wrong modulation, wrong ranges, etc.

---

### 7. `SF2Engine` region API has import errors and incomplete wiring

- `_create_base_region` correctly imports `SF2Region` via `from ..partial.sf2_region import SF2Region`.
- `create_region` at the bottom does:

  ```452:453:synth/engine/sf2_engine.py
  from .partial.sf2_region import SF2Region
  ```

  which is wrong relative import (engine → partial requires `..partial.sf2_region`). That will raise an `ImportError`.

- `get_preset_info` / `get_all_region_descriptors` operate by directly poking into `soundfont_manager.loaded_files` and calling `_get_or_load_preset` (a private method on `SF2SoundFont`). That’s tolerable but tightly coupled and still only builds descriptors; no full, layered voice/partial generation path is present.

**Impact:** The newer “region‑based architecture” is clearly in transition and not yet usable in its current form.

---

### 8. Loop handling and sample addressing are fragile

Multiple loop implementations exist:

- In `SF2Partial._handle_sample_looping` (loop_mode 0/1/3).
- In `SF2Region._handle_sf2_looping`.

Because loop info comes from either `params['loop']` in `SF2Partial`, or `get_sample_loop_info` in `SF2Region` (which doesn’t exist), and because coarse addressing generators are mapped incorrectly, **loop start/end positions are very likely wrong or default to the whole sample**.

Combined with the earlier mapping bug `sample_id` vs `exclusiveClass` in the SF2 core package, it’s very easy for regions/partials to be created without correct loop metadata at all.

---

### 9. Misc issues (less critical than the above, but still real)

- `SF2Engine._cents_to_frequency` delegates to `sf2_constants.cents_to_frequency`, which itself uses a weird `frequency_to_cents` implementation (earlier discussion) – not fatal, but mathematically off if you ever invert it.
- Several envelope/timecent conversion helpers across engine/region/partial use slightly different conventions; they’re not unified and sometimes ignore the `-12000` sentinel.

---

### Overall verdict on the audio synthesis pipeline

- The **design** is ambitious and sensible: SF2Engine → Preset/Region descriptors → SF2Region → SF2Partial, with pooled envelopes/filters/LFOs and modulation matrix integration.
- The **implementation**, however, is mid‑refactor and currently not in a working state for SF2 playback:
  - `SF2Partial` is not instantiable due to `__slots__` issues.
  - Region → partial and engine → SF2 core APIs don’t line up (wrong constructors, missing manager methods, mismatched parameter shapes).
  - Generator mapping is inconsistent with the SF2 spec in several places, so even if you get sound, it won’t match the soundfont’s programming.

If your goal is a functioning SF2 pipeline, the priority fixes would be:

1. Fix `__slots__` in `SF2Partial` (or remove them) and correct its constructor usage (`SF2Region._create_partial`).
2. Implement (or remove) the expected manager methods: `get_sample_info`, `get_sample_loop_info`, `get_zone`.
3. Define a **single, consistent parameter contract** between:
   - SF2SoundFont / SF2Region / SF2Engine and
   - `SF2Partial._load_sf2_parameters`  
   and update `_build_partial_params_from_generators` / `create_partial` to produce that shape.
4. Audit and correct SF2 generator ID mappings in `_load_sf2_generator_values` and the region/engine extraction helpers.

Once those are in place, more subtle issues (loop behavior, modulation depth scaling, mip‑mapping) can be iterated on with listening tests.