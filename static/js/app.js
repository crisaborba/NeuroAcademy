// CSRF helper: every POST/PUT/PATCH/DELETE fetch() call in this app must
// send the token from the <meta name="csrf-token"> tag rendered by the
// server, or the request is rejected with 403 (see csrf.py).
function getCsrfToken() {
  var meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

// ── Sistema de Conquistas (NeuroAcademy) ──────────────────────────────────
// Popup global inspirado em Playstation/Xbox/Steam (só inspiração, não
// cópia): canto inferior direito, glassmorphism, entra deslizando, some
// sozinho depois de ~4s. Qualquer página/bloco pode chamar
// window.NeuroAchievements.show({...}). Som é sintetizado via Web Audio
// (sem depender de arquivo externo), sempre curto e discreto.
window.NeuroAchievements = (function () {
  var host = null;
  var queue = [];
  var showing = false;

  function ensureHost() {
    if (!host) host = document.getElementById('achvHost');
    return host;
  }

  function playChime() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var notes = [880, 1174.66];
      notes.forEach(function (freq, i) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        var t0 = ctx.currentTime + i * 0.09;
        gain.gain.setValueAtTime(0, t0);
        gain.gain.linearRampToValueAtTime(0.09, t0 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.32);
        osc.connect(gain).connect(ctx.destination);
        osc.start(t0);
        osc.stop(t0 + 0.34);
      });
      setTimeout(function () { try { ctx.close(); } catch (e) {} }, 900);
    } catch (e) { /* Web Audio indisponível -- silencioso, nunca quebra a UI */ }
  }

  function confetti(count) {
    var confettiHost = document.getElementById('confettiHost');
    if (!confettiHost) return;
    var colors = ['#4D7EFF', '#9B59FF', '#00D4FF', '#FFD166', '#22c55e'];
    for (var i = 0; i < (count || 60); i++) {
      var piece = document.createElement('div');
      piece.className = 'confetti-piece';
      piece.style.left = (Math.random() * 100) + 'vw';
      piece.style.background = colors[Math.floor(Math.random() * colors.length)];
      piece.style.animationDuration = (2.2 + Math.random() * 1.6) + 's';
      piece.style.animationDelay = (Math.random() * 0.4) + 's';
      confettiHost.appendChild(piece);
      (function (el) { setTimeout(function () { el.remove(); }, 4200); })(piece);
    }
  }

  function renderNext() {
    if (showing || !queue.length) return;
    var h = ensureHost();
    if (!h) { queue.shift(); return; }
    var item = queue.shift();
    showing = true;

    var toast = document.createElement('div');
    toast.className = 'achv-toast';
    toast.setAttribute('role', 'status');
    toast.innerHTML =
      '<div class="achv-mascot" aria-hidden="true">' + (item.emoji || '🎉') + '</div>' +
      '<div class="achv-body">' +
        '<p class="achv-title">' + item.title + '</p>' +
        '<p class="achv-desc">' + (item.description || '') + '</p>' +
        (item.progressPct != null ? (
          '<div class="achv-progress-label"><span>PROGRESSO RUMO À PLATINA</span><span>' + item.progressPct + '%</span></div>' +
          '<div class="achv-progress-track"><div class="achv-progress-fill" style="width:0%"></div></div>'
        ) : '') +
      '</div>';
    h.appendChild(toast);

    requestAnimationFrame(function () {
      toast.classList.add('is-visible');
      if (item.progressPct != null) {
        var fill = toast.querySelector('.achv-progress-fill');
        requestAnimationFrame(function () { if (fill) fill.style.width = item.progressPct + '%'; });
      }
    });

    playChime();
    if (item.confetti) confetti(70);

    var duration = item.duration || 4000;
    setTimeout(function () {
      toast.classList.add('is-leaving');
      toast.classList.remove('is-visible');
      setTimeout(function () {
        toast.remove();
        showing = false;
        renderNext();
      }, 420);
    }, duration);
  }

  function show(opts) {
    queue.push(opts || {});
    renderNext();
  }

  return { show: show, confetti: confetti };
})();

// Fade-up on scroll for elements with .fade-up
(function () {
  var els = document.querySelectorAll('.fade-up');
  if (!els.length) return;
  if (!('IntersectionObserver' in window)) {
    els.forEach(function (el) { el.style.opacity = 1; });
    return;
  }
  var obs = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.style.opacity = 1;
        entry.target.style.transform = 'translateY(0)';
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  els.forEach(function (el) {
    el.style.opacity = 0;
    el.style.transform = 'translateY(24px)';
    el.style.transition = 'opacity .6s ease, transform .6s ease';
    obs.observe(el);
  });
})();

// Home page mini chat preview (static demo, not wired to backend for perf)
(function () {
  var sendBtn = document.getElementById('homeChatSend');
  var input = document.getElementById('homeChatInput');
  var body = document.getElementById('homeChatBody');
  if (!sendBtn || !input || !body) return;

  function bubble(text, user) {
    var wrap = document.createElement('div');
    wrap.className = 'chat-msg' + (user ? ' user' : '');
    var b = document.createElement('div');
    b.className = 'chat-bubble';
    b.textContent = text;
    wrap.appendChild(b);
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  function send() {
    var text = input.value.trim();
    if (!text) return;
    bubble(text, true);
    input.value = '';
    setTimeout(function () {
      bubble('Entendido! Estou preparando uma recomendação personalizada. Acesse a plataforma para continuar com o assistente completo.', false);
    }, 700);
  }

  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter') send(); });
})();

// ── Barras de progresso animadas de bloco de aula (.pg-fill) ─────────────
// Anima de 0% até o valor real quando o bloco entra na tela, uma única vez.
// Usado pelo bloco "progress_header" (Bloco 1 da Aula 1) e reaproveitável
// por qualquer outro bloco que use a mesma marcação (data-pct).
(function () {
  var fills = document.querySelectorAll('.pg-fill[data-pct]');
  if (!fills.length) return;
  if (!('IntersectionObserver' in window)) {
    fills.forEach(function (f) { f.style.width = f.dataset.pct + '%'; });
    return;
  }
  var obs = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.style.width = entry.target.dataset.pct + '%';
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });
  fills.forEach(function (f) { obs.observe(f); });
})();
