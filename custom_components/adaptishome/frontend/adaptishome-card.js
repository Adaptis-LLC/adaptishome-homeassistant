/* Картка AdaptisHome для дашборду Home Assistant: стан обʼєкта, активний канал, канали з затримкою і доступністю за
   добу, остання подія. Без залежностей (Mushroom не потрібен): звичайний custom element у стилі компактних карток HA.
   Конфігурація: { type: custom:adaptishome-card, entity: sensor.<обʼєкт>_status } — решту сутностей картка знаходить
   сама через пристрій, до якого належить ця сутність. Інтеграція реєструє файл як ресурс Lovelace сама. */
const T = {
  uk: {ok: 'На звʼязку', failover: 'На резерві', offline: 'Не на звʼязку', new: 'Чекає підключення', unavailable: 'Немає даних',
       active: 'Активний', ready: 'Готовий', waiting: 'Очікує', down: 'Не готовий', disabled: 'Вимкнено', unplugged: 'Не підключено', recovering: 'Перевіряється',
       via: 'Інтернет через', day: 'за добу', uptime: 'Інтернет за 30 днів', saves: 'спрацювань резерву',
       ev_failover: 'Перемикання на', ev_return: 'Повернення на', ev_boot: 'Перезавантаження', ev_config: 'Нова конфігурація',
       noevents: 'Подій ще не було', pick: 'Оберіть сутність «Стан» обʼєкта AdaptisHome'},
  en: {ok: 'Online', failover: 'On backup', offline: 'Offline', new: 'Waiting for device', unavailable: 'No data',
       active: 'Active', ready: 'Ready', waiting: 'Waiting', down: 'Down', disabled: 'Disabled', unplugged: 'Not connected', recovering: 'Recovering',
       via: 'Internet via', day: 'last 24 h', uptime: 'Internet uptime, 30 days', saves: 'failovers',
       ev_failover: 'Failover to', ev_return: 'Back to', ev_boot: 'Reboot', ev_config: 'New configuration',
       noevents: 'No events yet', pick: 'Pick the AdaptisHome «Status» entity'},
};
const ICON = {fiber: 'mdi:ethernet', cable: 'mdi:ethernet', dish: 'mdi:satellite-variant', lte: 'mdi:signal-4g'};
const COLOR = {ok: 'var(--success-color, #2e7d32)', failover: 'var(--warning-color, #ef6c00)', offline: 'var(--error-color, #c62828)',
               new: 'var(--secondary-text-color)', unavailable: 'var(--secondary-text-color)'};
const CH_COLOR = {active: 'var(--success-color, #2e7d32)', ready: 'var(--info-color, #1f6fe0)', waiting: 'var(--warning-color, #ef6c00)',
                  down: 'var(--error-color, #c62828)', disabled: 'var(--disabled-text-color, #9e9e9e)',
                  unplugged: 'var(--disabled-text-color, #9e9e9e)', recovering: 'var(--warning-color, #ef6c00)'};
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

class AdaptisHomeCard extends HTMLElement {
  static getConfigElement() { return document.createElement('adaptishome-card-editor'); }
  static getStubConfig(hass) {
    const e = Object.values(hass.entities || {}).find(x => x.platform === 'adaptishome' && x.translation_key === 'status');
    return {entity: e ? e.entity_id : ''};
  }
  setConfig(config) { this._config = config; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }
  getCardSize() { return 4; }

  // сутності обʼєкта: усі з того самого пристрою, що й сутність «Стан»; канали — за атрибутами channel/priority
  _collect() {
    const h = this._hass, reg = h.entities || {}, me = reg[this._config.entity];
    if (!me || !me.device_id) return null;
    const mine = Object.values(reg).filter(e => e.device_id === me.device_id && e.platform === 'adaptishome');
    const by = k => mine.filter(e => e.translation_key === k).map(e => h.states[e.entity_id]).filter(Boolean);
    const one = k => by(k)[0];
    const chans = {};
    for (const k of ['channel_state', 'channel_rtt', 'channel_ready']) {
      for (const s of by(k)) { const id = s.attributes.channel; if (!id) continue; (chans[id] = chans[id] || {id})[k] = s; }
    }
    const channels = Object.values(chans).sort((a, b) => ((a.channel_state || {}).attributes.priority || 9) - ((b.channel_state || {}).attributes.priority || 9));
    return {status: h.states[this._config.entity], active: one('active'), rtt: one('rtt'), event: one('event'), channels,
            device: h.devices && h.devices[me.device_id]};
  }

  _render() {
    if (!this._hass || !this._config) return;
    const lang = (this._hass.locale || {}).language || this._hass.language || 'en', t = T[lang.startsWith('uk') ? 'uk' : 'en'];
    const d = this._config.entity ? this._collect() : null;
    if (!this.shadowRoot) this.attachShadow({mode: 'open'});
    if (!d || !d.status) { this.shadowRoot.innerHTML = `<ha-card><div class="e">${esc(t.pick)}</div></ha-card>${this._css()}`; return; }
    const st = d.status.state in COLOR ? d.status.state : 'unavailable', a = d.status.attributes, name = this._config.name || (d.device && d.device.name) || '';
    const rtt = d.rtt && !isNaN(+d.rtt.state) ? `${Math.round(+d.rtt.state)} ms` : '';
    const ev = d.event && d.event.attributes.event_type ? d.event : null;
    const evText = ev ? ({failover: `${t.ev_failover} ${esc(ev.attributes.to)}` + (ev.attributes.from && ev.attributes.from.length ? ` · ${esc(ev.attributes.from.join(', '))} ↓` : ''),
                          return: `${t.ev_return} ${esc(ev.attributes.to)}`, boot: t.ev_boot, config: t.ev_config}[ev.attributes.event_type] || ev.attributes.event_type) : t.noevents;
    const evTime = ev ? new Date(ev.state).toLocaleString(lang, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : '';
    const up = a.uptime30_total_pct != null ? `${t.uptime}: <b>${esc(a.uptime30_total_pct)}%</b>` + (a.saves30 ? ` · ${esc(a.saves30)} ${t.saves}` : '') : '';
    const chip = c => {
      const s = c.channel_state, state = s ? s.state : 'disabled', col = CH_COLOR[state] || CH_COLOR.disabled;
      const r = c.channel_rtt && !isNaN(+c.channel_rtt.state) ? `${Math.round(+c.channel_rtt.state)} ms` : (t[state] || state);
      const nm = s && s.attributes.channel_name || c.id;
      const avail = s && s.attributes.avail_24h ? s.attributes.avail_24h : '';
      return `<div class="ch" style="--c:${col}" title="${esc(s ? s.attributes.desc || '' : '')}">
        <div class="ct"><ha-icon icon="${ICON[s && s.attributes.kind] || 'mdi:web'}"></ha-icon><span class="cn">${esc(nm)}</span><span class="dot"></span></div>
        <div class="cv">${esc(r)}</div>
        ${avail ? `<div class="av" title="${esc(t.day)}">${[...avail].map(x => `<i class="${x}"></i>`).join('')}</div>` : ''}
      </div>`;
    };
    this.shadowRoot.innerHTML = `<ha-card>
      <div class="hd"><div class="nm">${esc(name)}</div><div class="pill" style="--c:${COLOR[st]}">${esc(t[st])}</div></div>
      <div class="main"><ha-icon icon="mdi:shield-check-outline" style="color:${COLOR[st]}"></ha-icon>
        <div><div class="l">${t.via}</div><div class="v">${esc(d.active ? d.active.state : '—')}${rtt ? ` <small>${rtt}</small>` : ''}</div></div></div>
      <div class="chs">${d.channels.map(chip).join('')}</div>
      <div class="ft"><span>${evText}</span><time>${esc(evTime)}</time></div>
      ${up ? `<div class="ft up">${up}</div>` : ''}
    </ha-card>${this._css()}`;
  }

  _css() { return `<style>
    ha-card{padding:14px 16px;font-family:var(--primary-font-family, inherit);color:var(--primary-text-color);border-radius:var(--ha-card-border-radius,12px)}
    .e{color:var(--secondary-text-color);font-size:14px}
    .hd{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}
    .nm{font-weight:600;font-size:16px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .pill{--c:var(--secondary-text-color);color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600;white-space:nowrap}
    .main{display:flex;align-items:center;gap:12px;margin-bottom:12px}
    .main ha-icon{--mdc-icon-size:34px;background:color-mix(in srgb,currentColor 12%,transparent);border-radius:12px;padding:7px}
    .l{font-size:12px;color:var(--secondary-text-color)}.v{font-size:18px;font-weight:600}.v small{font-size:13px;font-weight:500;color:var(--secondary-text-color)}
    .chs{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px}
    .ch{--c:var(--secondary-text-color);background:color-mix(in srgb,var(--c) 9%,transparent);border-radius:12px;padding:8px 10px;min-width:0}
    .ct{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--secondary-text-color)}.ct ha-icon{--mdc-icon-size:16px;color:var(--c)}
    .cn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}.dot{width:8px;height:8px;border-radius:50%;background:var(--c);flex:none}
    .cv{font-size:15px;font-weight:600;margin-top:2px}
    .av{display:flex;gap:1px;margin-top:6px;height:6px}.av i{flex:1;border-radius:1px;background:var(--divider-color)}.av i.o{background:var(--success-color,#2e7d32)}.av i.x{background:var(--error-color,#c62828)}
    .ft{display:flex;justify-content:space-between;gap:10px;margin-top:12px;font-size:12px;color:var(--secondary-text-color)}
    .ft time{white-space:nowrap}.ft.up{margin-top:6px}
  </style>`; }
}

class AdaptisHomeCardEditor extends HTMLElement {
  setConfig(config) { this._config = config; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this._hass || !this._config) return;
    if (!this._el) {
      this._el = document.createElement('ha-form');
      this._el.addEventListener('value-changed', e => {
        this._config = {...this._config, ...e.detail.value};
        this.dispatchEvent(new CustomEvent('config-changed', {detail: {config: this._config}, bubbles: true, composed: true}));
      });
      this.appendChild(this._el);
    }
    const uk = ((this._hass.locale || {}).language || '').startsWith('uk');
    this._el.hass = this._hass;
    this._el.data = this._config;
    this._el.schema = [
      {name: 'entity', required: true, selector: {entity: {filter: {integration: 'adaptishome', domain: 'sensor'}}}},
      {name: 'name', selector: {text: {}}},
    ];
    this._el.computeLabel = s => s.name === 'entity' ? (uk ? 'Сутність «Стан» обʼєкта' : 'Object «Status» entity') : (uk ? 'Назва (необовʼязково)' : 'Name (optional)');
  }
}

customElements.define('adaptishome-card', AdaptisHomeCard);
customElements.define('adaptishome-card-editor', AdaptisHomeCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({type: 'adaptishome-card', name: 'AdaptisHome', description: 'Стан обʼєкта AdaptisHome: канали, затримка, події', preview: true});
