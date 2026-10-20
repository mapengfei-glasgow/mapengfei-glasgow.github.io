/* [[term]] previews, including pages reached through Turbo navigation. */
(() => {
  let notesPromise;
  let active;
  let timer;
  const panel = document.createElement('aside');
  panel.id = 'word-note-preview';
  panel.className = 'word-note-preview';
  panel.setAttribute('role', 'tooltip');
  panel.hidden = true;
  const close = () => {
    panel.hidden = true;
    active?.removeAttribute('aria-describedby');
    active = null;
  };
  const position = () => {
    if (!active) return;
    const rect = active.getBoundingClientRect();
    panel.style.left = `${Math.max(12, Math.min(rect.left, innerWidth - panel.offsetWidth - 12))}px`;
    panel.style.top = `${Math.max(12, Math.min(rect.bottom + 8, innerHeight - panel.offsetHeight - 12))}px`;
  };
  const show = (button, note) => {
    clearTimeout(timer);
    close();
    active = button;
    panel.replaceChildren();
    const title = document.createElement('h3');
    title.textContent = button.textContent;
    panel.append(title);
    const fields = note ? [['音标', note.pronunciation], ['词性', note.part_of_speech], ['释义', note.meaning], ['Explanation', note.explanation], ['原文', note.context]] : [['', 'Definition not generated yet.']];
    for (const [label, value] of fields) {
      if (!value) continue;
      const p = document.createElement('p');
      p.textContent = (label ? `${label}: ` : '') + value;
      panel.append(p);
    }
    button.setAttribute('aria-describedby', panel.id);
    panel.hidden = false;
    position();
  };
  const later = () => { timer = setTimeout(close, 180); };
  panel.addEventListener('pointerenter', () => clearTimeout(timer));
  panel.addEventListener('pointerleave', later);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  document.addEventListener('click', e => { if (!panel.contains(e.target) && !e.target.closest('.word-note-term')) close(); });
  window.addEventListener('resize', position);
  window.addEventListener('scroll', position, true);
  document.addEventListener('turbo:before-cache', () => {
    close();
    document.querySelectorAll('.word-note-term').forEach(button => {
      button.replaceWith(document.createTextNode(`[[${button.textContent}]]`));
    });
  });
  async function init() {
    close();
    document.body.append(panel);
    const config = document.querySelector('meta[name="word-notes"]');
    if (!config) return;
    notesPromise ||= fetch(config.content).then(r => { if (!r.ok) throw Error('notes'); return r.json(); }).catch(() => { notesPromise = null; return {}; });
    const url = location.pathname;
    const all = await notesPromise;
    if (location.pathname !== url) return;
    const notes = all[url] || {};
    // Episode pages keep their sentences in front matter and render them as
    // <ol class="sentences"><li class="sentence"><span class="text">…</span>,
    // so their markers never sit inside a .post-content body.
    document.querySelectorAll('.post-content, .md-content, .sentences .text').forEach(root => {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode(node) {
        return node.parentElement.closest('a,button,code,pre,script,style,textarea,.katex,mjx-container') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }});
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      for (const node of nodes) {
        const matches = [...node.textContent.matchAll(/\[\[([^\[\]\n]{1,120})\]\]/g)];
        if (!matches.length) continue;
        const fragment = document.createDocumentFragment();
        let offset = 0;
        for (const match of matches) {
          fragment.append(node.textContent.slice(offset, match.index));
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'word-note-term';
          button.textContent = match[1].trim();
          button.addEventListener('pointerenter', () => show(button, notes[button.textContent]));
          button.addEventListener('pointerleave', later);
          button.addEventListener('focus', () => show(button, notes[button.textContent]));
          button.addEventListener('blur', later);
          button.addEventListener('click', e => { e.stopPropagation(); show(button, notes[button.textContent]); });
          fragment.append(button);
          offset = match.index + match[0].length;
        }
        fragment.append(node.textContent.slice(offset));
        node.replaceWith(fragment);
      }
    });
  }
  document.addEventListener('turbo:load', init);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
