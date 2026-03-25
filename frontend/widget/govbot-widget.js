/**
 * GovBot KR 웹 채팅 위젯 v1.0
 * 사용법: <script src="govbot-widget.js" data-tenant="your-slug" data-api="https://your-api.com"></script>
 */
;(function () {
  'use strict'

  var cfg = (function () {
    var el = document.currentScript
    return {
      tenant: el ? el.getAttribute('data-tenant') || '' : '',
      api: el ? el.getAttribute('data-api') || '' : '',
      title: el ? el.getAttribute('data-title') || 'AI 민원 도우미' : 'AI 민원 도우미',
      color: el ? el.getAttribute('data-color') || '#2563eb' : '#2563eb',
    }
  })()

  var style = document.createElement('style')
  style.textContent = [
    '#govbot-fab{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:' + cfg.color + ';color:#fff;border:none;font-size:26px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.2);z-index:9999;display:flex;align-items:center;justify-content:center}',
    '#govbot-window{position:fixed;bottom:90px;right:24px;width:360px;height:520px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.15);z-index:9998;display:none;flex-direction:column;overflow:hidden;font-family:Apple SD Gothic Neo,system-ui,sans-serif}',
    '#govbot-window.open{display:flex}',
    '#govbot-header{background:' + cfg.color + ';color:#fff;padding:14px 16px;font-weight:700;font-size:15px;display:flex;justify-content:space-between;align-items:center}',
    '#govbot-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0;line-height:1}',
    '#govbot-msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}',
    '.govbot-msg{max-width:80%;padding:10px 13px;border-radius:14px;font-size:13px;line-height:1.5;word-break:break-word}',
    '.govbot-msg.user{align-self:flex-end;background:' + cfg.color + ';color:#fff;border-bottom-right-radius:4px}',
    '.govbot-msg.bot{align-self:flex-start;background:#f3f4f6;color:#222;border-bottom-left-radius:4px}',
    '.govbot-meta{font-size:10px;color:#9ca3af;margin-top:3px;align-self:flex-start}',
    '#govbot-form{display:flex;gap:8px;padding:12px;border-top:1px solid #f0f0f0}',
    '#govbot-input{flex:1;padding:9px 13px;border:1px solid #d1d5db;border-radius:20px;font-size:13px;outline:none}',
    '#govbot-send{padding:9px 16px;background:' + cfg.color + ';color:#fff;border:none;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer}',
  ].join('')
  document.head.appendChild(style)

  var fab = document.createElement('button')
  fab.id = 'govbot-fab'
  fab.title = cfg.title
  fab.textContent = '💬'

  var win = document.createElement('div')
  win.id = 'govbot-window'
  win.innerHTML = [
    '<div id="govbot-header">' + cfg.title + '<button id="govbot-close">✕</button></div>',
    '<div id="govbot-msgs"></div>',
    '<form id="govbot-form"><input id="govbot-input" type="text" placeholder="질문을 입력하세요..." autocomplete="off" /><button id="govbot-send" type="submit">전송</button></form>',
  ].join('')

  document.body.appendChild(fab)
  document.body.appendChild(win)

  var msgs = win.querySelector('#govbot-msgs')
  var input = win.querySelector('#govbot-input')
  var form = win.querySelector('#govbot-form')

  function addMsg(role, text, meta) {
    var div = document.createElement('div')
    div.className = 'govbot-msg ' + role
    div.textContent = text
    msgs.appendChild(div)
    if (meta) {
      var m = document.createElement('div')
      m.className = 'govbot-meta'
      m.textContent = meta
      msgs.appendChild(m)
    }
    msgs.scrollTop = msgs.scrollHeight
  }

  function greet() {
    addMsg('bot', '안녕하세요! 무엇을 도와드릴까요? 궁금하신 민원 사항을 입력해주세요.')
  }

  var busy = false

  form.addEventListener('submit', function (e) {
    e.preventDefault()
    var text = input.value.trim()
    if (!text || busy) return
    input.value = ''
    addMsg('user', text)
    busy = true

    var endpoint = cfg.api + '/skill/' + cfg.tenant
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userRequest: {
          utterance: text,
          user: { id: 'web-' + Math.random().toString(36).slice(2, 10) },
        },
      }),
    })
      .then(function (r) { return r.json() })
      .then(function (data) {
        var answer = ''
        try { answer = data.template.outputs[0].simpleText.text } catch (ex) { answer = '응답을 받아오지 못했습니다.' }
        addMsg('bot', answer)
      })
      .catch(function () { addMsg('bot', '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.') })
      .finally(function () { busy = false })
  })

  fab.addEventListener('click', function () {
    var isOpen = win.classList.toggle('open')
    if (isOpen && msgs.children.length === 0) greet()
    if (isOpen) input.focus()
  })

  win.querySelector('#govbot-close').addEventListener('click', function () {
    win.classList.remove('open')
  })
})()
