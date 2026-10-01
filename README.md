# AdaptisHome у Home Assistant

*English summary at the bottom.*

Інтеграція показує в Home Assistant стан обʼєктів AdaptisHome: через який канал іде інтернет, чи працює резерв,
затримка й втрати по каналах, трафік, статистика за 30 днів, події (перемикання, повернення, перезавантаження).
Дані беруться з хаба (той самий логін і пароль, що в панелі), опитування раз на 30 с — як застосунки клієнта. Керувати
пристроєм з HA не можна, лише дивитись: так само, як у панелі.

## Встановити

Через HACS (найпростіше, оновлення теж через нього):

1. HACS → три крапки праворуч угорі → **Custom repositories** → `https://github.com/RohaDev/adaptishome-homeassistant`, тип
   **Integration** → Add.
2. HACS → знайти **AdaptisHome** → Download → перезавантажити Home Assistant.

Потрібен Home Assistant **2026.3 або новіший** (логотип і картка беруться з самої інтеграції).

Без HACS: скопіювати теку `custom_components/adaptishome` з цього репозиторію в `config/custom_components/` на
Home Assistant і перезавантажити його.

Далі **Налаштування → Пристрої та служби → Додати інтеграцію → AdaptisHome**: логін і пароль з панелі AdaptisHome. Якщо обʼєктів кілька — обрати, які показувати (змінити
можна потім у «Налаштувати» інтеграції). Один обʼєкт = один пристрій HA з моделлю й серійником MikroTik.

## Що зʼявляється

| Сутність | Що це |
|---|---|
| `sensor.<обʼєкт>_status` | На звʼязку / На резерві / Не на звʼязку / Чекає підключення; в атрибутах серійник, модель, версія конфігурації |
| `sensor.<обʼєкт>_active_channel` | назва каналу, через який іде інтернет |
| `sensor.<обʼєкт>_latency` | затримка активного каналу, мс |
| `sensor.<обʼєкт>_traffic_today`, `…_internet_uptime_30_days`, `…_failovers_30_days` | трафік за сьогодні (ГБ), частка часу з інтернетом і скільки разів спрацював резерв за 30 днів |
| `binary_sensor.<обʼєкт>_online`, `…_internet_via_backup` | пристрій на звʼязку; інтернет зараз через резерв (problem) |
| `sensor.<обʼєкт>_<канал>_state`, `…_latency` | по кожному каналу: стан (Активний / Готовий / Очікує / Не готовий), затримка |
| `binary_sensor.<обʼєкт>_<канал>` | канал готовий (connectivity) |
| `event.<обʼєкт>_event` | остання подія: `failover`, `return`, `boot`, `config`; в атрибутах `to`, `from` |

Вимкнені за замовчуванням (увімкнути в налаштуваннях сутності): прийом/передача Мбіт/с, втрати і трафік за місяць по
каналах, час роботи пристрою. Для LTE-каналу є ще сигнал (dBm).

Кожна нова подія ще йде на шину HA як `adaptishome_event` з `object_id`, `object`, `kind`, `to`, `from`, `ts`.

## Картка для дашборду

Разом з інтеграцією приходить картка **AdaptisHome** (окремо нічого ставити не треба, Mushroom не потрібен): у
редакторі дашборду «Додати картку» → «AdaptisHome» → обрати сутність «Стан» обʼєкта. Показує стан, через який канал
іде інтернет і затримку, плитку на кожен канал (стан, затримка, доступність за добу смужкою), останню подію та
статистику за 30 днів. Кольори — з теми HA, тож пасує і до світлої, і до темної.

```yaml
type: custom:adaptishome-card
entity: sensor.budinok_status
name: Будинок        # необовʼязково, типово — назва обʼєкта
```

Якщо дашборди у вас у YAML-режимі, ресурс додайте самі: `url: /adaptishome/adaptishome-card.js`, `type: module`.

## Приклад автоматизації: сповіщення про резерв

```yaml
alias: AdaptisHome — інтернет через резерв
triggers:
  - trigger: event
    event_type: adaptishome_event
    event_data:
      kind: failover
actions:
  - action: notify.mobile_app_iphone
    data:
      title: "{{ trigger.event.data.object }}"
      message: "Інтернет перейшов на {{ trigger.event.data.to }}: {{ trigger.event.data.from | join(', ') }} не відповідає"
```

Повернення — так само з `kind: return`. Для картки на панелі досить `sensor.<обʼєкт>_status` і
`sensor.<обʼєкт>_active_channel`; графік затримки по каналах — звичайна history-graph по `…_<канал>_latency`.

## In English

Home Assistant integration for **AdaptisHome** — Adaptis' multi-WAN internet failover box (MikroTik between up to four
internet links and the customer's router). It reads object state from the AdaptisHome hub with the same login as the
panel: status, active channel, latency, traffic, 30-day statistics, per-channel state, and events (failover, return,
reboot, config). Install via HACS as a custom repository (`https://github.com/RohaDev/adaptishome-homeassistant`,
type Integration), then add the **AdaptisHome** integration. Read-only, cloud polling every 30 s.
