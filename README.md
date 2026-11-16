# Kúrenie AI – Home Assistant integration

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md) [![Slovenčina](https://img.shields.io/badge/jazyk-Sloven%C4%8Dina-green.svg)](README.sk.md)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Version](https://img.shields.io/github/v/tag/soso8782/samsung_heat_pump-ai-control-home-assistant-integration?label=version&sort=semver)](https://github.com/soso8782/samsung_heat_pump-ai-control-home-assistant-integration/tags)

A custom component for Home Assistant that connects HA to the
**[Kúrenie AI](https://github.com/soso8782/samsung_heat_pump-ai-control)** web app – an AI agent for Samsung EHS heat pumps
(Mono and Split, controlled through ESPHome and the NASA bus). In Home Assistant it creates one device with entities for
monitoring rooms, water, the compressor, DHW and the agent, and lets you change the agent mode and the target room temperature.

The integration is translated into Slovak and English. The app itself (web UI, notifications and the AI agent) is also available
in Slovak and English: the web UI is switched with the SK/EN switch, and the language of the agent and notifications is set with
`UI_LANG` or in the app under Settings → "Language of notifications and the agent".

*Slovak documentation: [README.sk.md](README.sk.md).*

## Requirements

- a running **Kúrenie AI app, version 2.3.0 or newer** (the `/api/ha/v1` interface),
- Home Assistant 2024.11 or newer,
- a network connection from Home Assistant to the app (data is read locally, `local_polling`, every 30 s by default).

## Installation

**Via HACS (custom repository):**
1. HACS → menu ⋮ at the top right → **Custom repositories**.
2. Repository: `https://github.com/soso8782/samsung_heat_pump-ai-control-home-assistant-integration`, category **Integration**.
3. Install **Kúrenie AI** and restart Home Assistant.

**Manually:** copy the `custom_components/kurenie_ai` folder to `config/custom_components/` and restart Home Assistant.

## Setup

1. In the Kúrenie AI app open **Settings → Home Assistant integration** and click **Create key**.
   The key is shown only once (only its SHA-256 fingerprint is stored on the server). A new key replaces the old one, **Revoke key** disconnects the integration.
2. In Home Assistant: **Settings → Devices & services → Add integration → Kúrenie AI**.
3. Enter the app address (e.g. `http://192.168.1.50`) and the key.
4. You can change the refresh interval (15 – 300 s) with **Configure** on the integration.
   When you revoke or replace the key, Home Assistant offers to re-authenticate.

## Entities

Device "Kúrenie AI – <heat pump model>" (manufacturer Samsung).

| Type | Entities |
|---|---|
| sensor | outdoor temperature; temperature of each room (attributes `min_target`, `reference`); flow temperature, return temperature, target flow temperature from the heating curve, Delta T; compressor frequency; curve offset; DHW temperature (if there is DHW); error code; agent status (ok / pozor / problém); last agent assessment (full text in the `summary` attribute); alerts (count, list in the `alerts` attribute) |
| binary_sensor | compressor running; defrost; DHW heating (if there is DHW); problem (alert or error code ≠ 0); connection of the ESP, the collector and Home Assistant |
| select | agent mode (off / advise only / control) |
| number | target room temperature (step 0.5 °C, range given by the app) |
| button | run the agent now; start DHW heating (if there is DHW) |

After each action the data is refreshed immediately. If the app rejects an action (e.g. DHW heating cannot be started now), Home Assistant shows its message.

The integration does not provide consumption and COP for the Energy dashboard – the app publishes those via MQTT (`ha_pub.py`).

## Troubleshooting

- **Failed to connect:** check the address (http or https) and that the app is running.
- **Key is invalid:** create a new key in the app and enter it again.
- **Detailed logs:**
  ```yaml
  logger:
    logs:
      custom_components.kurenie_ai: debug
  ```

## Tests

```bash
python -X utf8 -m unittest discover -s tests -v
```

The tests run without Home Assistant (pure logic, syntax, JSON, translations). The test that checks the paths against the server
runs if the `KURENIE_APP` variable points to the Kúrenie AI app folder.
