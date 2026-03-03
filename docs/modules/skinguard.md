# SkinGuard

Detects and rejects invalid skins on player join: 4D geometry, tiny models, invisible/transparent textures, and non-standard dimensions.

## How It Works

SkinGuard runs **4 checks** on every player join:

### 1. Geometry Name Validation
Only standard Bedrock geometry models are allowed:
- `geometry.humanoid.custom`
- `geometry.humanoid.customSlim`
- `geometry.humanoid` (and baby variants)

Custom model names (e.g., `geometry.4d_wings`, `geometry.tiny`) → **kicked**.

### 2. Geometry Data Parsing
If the skin includes custom geometry JSON, SkinGuard parses it:
- **Bone count**: Must have at least 4 bones (head, body, arms)
- **Model volume**: Total cube volume must exceed 500 units (standard Steve ≈ 2000+)
- **Sub-pixel bones**: Cubes smaller than 0.5 pixels in any dimension → **flagged**

This prevents tiny/microscopic models that shrink the player's hitbox.

### 3. Transparency Detection
Scans the RGBA pixel data of the skin texture:
- If **>95% of pixels** are fully transparent → **invisible skin → kicked**
- If fewer than **50 visible pixels** → **near-invisible → kicked**

### 4. Dimension Validation
Only valid Bedrock skin sizes are accepted:
- 64×32, 64×64, 128×128, 256×256

Non-standard dimensions → **kicked**.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Toggle | ON | `/ac-skinguard` |
| Sensitivity | 1–10 | `/ac-modules skinguard sensitivity <1-10>` |

## Why This Matters

4D skins and tiny geometries create unfair PvP advantages:
- **Tiny hitbox**: Other players' attacks miss because the collision box is microscopic
- **Invisible**: Players can move unseen without admin vanish
- **Custom geometry**: Can add wings, extra limbs, or other distracting visual elements

SkinGuard ensures all players use standard-sized, visible models.

## Toggle Command

```
/ac-skinguard
```
