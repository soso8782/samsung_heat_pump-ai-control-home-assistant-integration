# Kúrenie AI – integrácia do Home Assistanta

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Verzia](https://img.shields.io/github/v/tag/soso8782/samsung_heat_pump-ai-control-home-assistant-integration?label=verzia&sort=semver)](https://github.com/soso8782/samsung_heat_pump-ai-control-home-assistant-integration/tags)

Vlastná integrácia (custom component) pre Home Assistant, ktorá pripojí HA na web aplikáciu
**[Kúrenie AI](https://github.com/soso8782/kurenie_ai_samsung_heat_pump)** – AI agenta pre tepelné čerpadlá Samsung EHS
(Mono aj Split, riadené cez ESPHome a zbernicu NASA). V Home Asistante vytvorí jedno zariadenie s entitami na sledovanie
izieb, vody, kompresora, TÚV a agenta a umožní meniť režim agenta a cieľovú izbovú teplotu.

*English summary below.*

## Požiadavky

- bežiaca aplikácia **Kúrenie AI verzie 2.3.0 alebo novšej** (rozhranie `/api/ha/v1`),
- Home Assistant 2024.11 alebo novší,
- sieťové spojenie z Home Assistanta na aplikáciu (dáta sa čítajú lokálne, `local_polling`, predvolene každých 30 s).

## Inštalácia

**Cez HACS (vlastný repozitár):**
1. HACS → menu ⋮ vpravo hore → **Vlastné repozitáre**.
2. Repozitár: `https://github.com/soso8782/samsung_heat_pump-ai-control-home-assistant-integration`, kategória **Integrácia**.
3. Nainštaluj **Kúrenie AI** a reštartuj Home Assistant.

**Ručne:** skopíruj priečinok `custom_components/kurenie_ai` do `config/custom_components/` a reštartuj Home Assistant.

## Nastavenie

1. V aplikácii Kúrenie AI otvor **Nastavenia → Integrácia do Home Assistanta** a daj **Vytvoriť kľúč**.
   Kľúč sa zobrazí iba raz (na serveri je uložený len jeho odtlačok SHA-256). Nový kľúč nahradí starý, **Zrušiť kľúč** integráciu odpojí.
2. V Home Assistante: **Nastavenia → Zariadenia a služby → Pridať integráciu → Kúrenie AI**.
3. Zadaj adresu aplikácie (napr. `http://192.168.1.50`) a kľúč.
4. Interval obnovy (15 – 300 s) zmeníš cez **Konfigurovať** pri integrácii.
   Keď kľúč zrušíš alebo vymeníš, Home Assistant ponúkne opätovné prihlásenie.

## Entity

Zariadenie „Kúrenie AI – <model tepelného čerpadla>“ (výrobca Samsung).

| Typ | Entity |
|---|---|
| sensor | vonkajšia teplota; teplota každej izby (atribúty `min_target`, `reference`); výstupná teplota vody, spiatočka, cieľ podľa krivky, Delta T; frekvencia kompresora; posun krivky; teplota TÚV (ak je TÚV); chybový kód; stav agenta (ok / pozor / problém); posledné hodnotenie agenta (celý text v atribúte `summary`); poplachy (počet, zoznam v atribúte `alerts`) |
| binary_sensor | kompresor beží; odmrazovanie; ohrev TÚV (ak je TÚV); problém (poplach alebo chybový kód ≠ 0); pripojenie ESP, zberača a Home Assistanta |
| select | režim agenta (vypnutý / radí / riadi) |
| number | cieľová izbová teplota (krok 0,5 °C, rozsah podľa aplikácie) |
| button | spustiť agenta teraz; spustiť ohrev TÚV (ak je TÚV) |

Po každej akcii sa dáta obnovia hneď. Ak aplikácia akciu odmietne (napr. ohrev TÚV teraz nejde), Home Assistant zobrazí jej správu.

Spotrebu a COP pre panel Energia integrácia neprináša – tie posiela aplikácia cez MQTT (`ha_pub.py`).

## Riešenie problémov

- **Nepodarilo sa pripojiť:** skontroluj adresu (http alebo https) a či aplikácia beží.
- **Kľúč je neplatný:** vytvor v aplikácii nový kľúč a zadaj ho znova.
- **Podrobné záznamy:**
  ```yaml
  logger:
    logs:
      custom_components.kurenie_ai: debug
  ```

## Testy

```bash
python -X utf8 -m unittest discover -s tests -v
```

Testy bežia bez Home Assistanta (čistá logika, syntax, JSON, preklady). Test zhody ciest so serverom sa spustí,
ak premenná `KURENIE_APP` ukazuje na priečinok aplikácie Kúrenie AI.

---

## English

Custom Home Assistant integration for **[Kúrenie AI](https://github.com/soso8782/kurenie_ai_samsung_heat_pump)**, an AI agent
for Samsung EHS heat pumps. It creates one device with sensors (rooms, outdoor, water temperatures, Delta T, compressor,
curve shift, hot water, error code, agent status and alerts), binary sensors, an agent-mode select, a room-target number and
buttons (run agent now, hot-water boost). Translations: Slovak and English.

**Install:** HACS → Custom repositories → this repository URL, category *Integration* → install **Kúrenie AI** → restart HA.
**Configure:** in the app open *Settings → Home Assistant integration*, create a key (shown once), then in HA add the
**Kúrenie AI** integration with the app address and the key. Requires app version 2.3.0 or newer.
