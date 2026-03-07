// ============================================================
// Azure AI Foundry - Document Management Frontend
// ============================================================

const API = '/api/v1';

// ── Tab navigation ───────────────────────────────────────────

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    const tabId = `tab-${btn.dataset.tab}`;
    document.getElementById(tabId)?.classList.add('active');
  });
});

document.querySelectorAll('.inner-tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const parent = btn.closest('.tabs-inner');
    parent.querySelectorAll('.inner-tab-btn').forEach(b => b.classList.remove('active'));
    parent.querySelectorAll('.inner-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    parent.querySelector(`#inner-${btn.dataset.inner}`)?.classList.add('active');
  });
});

// ── Utilities ────────────────────────────────────────────────

function showLoading(resultId) {
  document.getElementById(resultId).innerHTML =
    '<div style="text-align:center;padding:2rem;color:var(--text-muted)"><div class="spinner"></div> Analyse en cours...</div>';
}

function showResult(resultId, html) {
  document.getElementById(resultId).innerHTML = html;
}

function showError(resultId, error) {
  const msg = error?.detail || error?.message || String(error);
  document.getElementById(resultId).innerHTML =
    `<div style="color:var(--danger);padding:.5rem"><strong>Erreur:</strong> ${escapeHtml(msg)}</div>`;
  toast(msg, 'error');
}

function toast(message, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function jsonBlock(data) {
  return `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}

function resultBlock(label, content) {
  return `<div class="result-block"><div class="label">${label}</div><div class="value">${content}</div></div>`;
}

function tagList(items, className = 'tag') {
  if (!items || items.length === 0) return '<span style="color:var(--text-muted)">Aucun</span>';
  return `<div class="tag-list">${items.map(t => `<span class="${className}">${escapeHtml(t)}</span>`).join('')}</div>`;
}

async function callApi(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json();
  if (!response.ok) throw data;
  return data;
}

async function postForm(path, formData) {
  return callApi(path, { method: 'POST', body: formData });
}

async function postJson(path, body) {
  return callApi(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ── Simple Markdown renderer ─────────────────────────────────

function renderMarkdown(text) {
  return text
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(.+)$/gm, (line) => {
      if (line.startsWith('<')) return line;
      return `<p>${line}</p>`;
    });
}

// ── Document Intelligence ────────────────────────────────────

document.getElementById('form-doc-analyze').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-doc-analyze');
  try {
    const fd = new FormData(e.target);
    const data = await postForm('/documents/analyze', fd);

    let html = '';
    html += resultBlock('Modèle utilisé', `<code>${data.model_id}</code>`);
    html += resultBlock('Pages', data.pages);
    html += resultBlock('Langues détectées', tagList(data.languages));

    if (data.extracted_text) {
      const preview = data.extracted_text.substring(0, 600);
      html += resultBlock('Texte extrait (aperçu)', `<pre>${escapeHtml(preview)}${data.extracted_text.length > 600 ? '...' : ''}</pre>`);
    }

    if (data.key_value_pairs?.length) {
      const kvHtml = data.key_value_pairs.slice(0, 15).map(kv =>
        `<tr><td style="padding:.3rem .5rem;font-weight:500">${escapeHtml(kv.key)}</td>
         <td style="padding:.3rem .5rem">${escapeHtml(kv.value || '')}</td>
         <td style="padding:.3rem .5rem;color:var(--text-muted)">${kv.confidence ? (kv.confidence * 100).toFixed(0) + '%' : ''}</td></tr>`
      ).join('');
      html += resultBlock('Paires Clé-Valeur', `<table style="width:100%;border-collapse:collapse;font-size:.8rem">
        <tr style="background:var(--bg)"><th style="padding:.3rem .5rem;text-align:left">Clé</th><th style="text-align:left">Valeur</th><th>Confiance</th></tr>
        ${kvHtml}</table>`);
    }

    if (data.tables?.length) {
      html += resultBlock('Tableaux détectés', `${data.tables.length} tableau(x) — <em>${data.tables.reduce((s, t) => s + t.cells.length, 0)} cellules</em>`);
    }

    showResult('result-doc-analyze', html);
  } catch (err) {
    showError('result-doc-analyze', err);
  }
});

// ── AI Language ──────────────────────────────────────────────

document.getElementById('form-nlp').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-nlp');
  try {
    const fd = new FormData(e.target);
    const ops = fd.getAll('ops');
    const body = {
      text: fd.get('text'),
      operations: ops,
    };
    const data = await postJson('/analysis/nlp', body);

    let html = '';

    if (data.detected_language) {
      html += resultBlock('Langue détectée', `<strong>${data.detected_language}</strong> (confiance: ${(data.language_confidence * 100).toFixed(0)}%)`);
    }

    if (data.sentiment) {
      const s = data.sentiment;
      const colors = { positive: '#107C10', neutral: '#6B7280', negative: '#D13438', mixed: '#FF8C00' };
      const color = colors[s.sentiment] || '#6B7280';
      html += resultBlock('Sentiment', `<span style="color:${color};font-weight:700">${s.sentiment.toUpperCase()}</span>
        — Positif: ${(s.confidence_scores.positive*100).toFixed(0)}%
        | Neutre: ${(s.confidence_scores.neutral*100).toFixed(0)}%
        | Négatif: ${(s.confidence_scores.negative*100).toFixed(0)}%`);
    }

    if (data.key_phrases?.length) {
      html += resultBlock('Phrases clés', tagList(data.key_phrases));
    }

    if (data.entities?.length) {
      const pills = data.entities.map(e =>
        `<span class="entity-pill">${escapeHtml(e.text)} <span style="opacity:.7;font-size:.7rem">${e.category}</span></span>`
      ).join('');
      html += resultBlock('Entités (NER)', `<div style="display:flex;flex-wrap:wrap;gap:.25rem;margin-top:.35rem">${pills}</div>`);
    }

    if (data.pii_entities?.length) {
      html += resultBlock('Entités PII', tagList(data.pii_entities.map(p => `${p.text} [${p.category}]`)));
      if (data.pii_redacted_text) {
        html += resultBlock('Texte anonymisé', `<pre>${escapeHtml(data.pii_redacted_text)}</pre>`);
      }
    }

    if (data.abstractive_summary) {
      html += resultBlock('Résumé abstractif', `<blockquote style="border-left:3px solid var(--azure-blue);padding:.5rem 1rem;background:var(--bg);border-radius:0 6px 6px 0">${escapeHtml(data.abstractive_summary)}</blockquote>`);
    }

    if (data.extractive_summary) {
      html += resultBlock('Résumé extractif', `<blockquote style="border-left:3px solid var(--success);padding:.5rem 1rem;background:var(--bg);border-radius:0 6px 6px 0">${escapeHtml(data.extractive_summary)}</blockquote>`);
    }

    showResult('result-nlp', html || '<em>Aucun résultat disponible.</em>');
  } catch (err) {
    showError('result-nlp', err);
  }
});

// ── Azure OpenAI - Q&A ───────────────────────────────────────

document.getElementById('form-qa').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-qa');
  try {
    const fd = new FormData(e.target);
    const body = {
      question: fd.get('question'),
      document_context: fd.get('document_context'),
      max_tokens: 1000,
      temperature: 0.3,
    };
    const data = await postJson('/analysis/qa', body);

    let html = resultBlock('Modèle', `<code>${data.model}</code>`) +
      resultBlock('Tokens utilisés', data.tokens_used) +
      resultBlock('Réponse', `<div style="background:var(--bg);padding:1rem;border-radius:6px;border-left:3px solid var(--azure-blue)">${escapeHtml(data.answer)}</div>`);

    showResult('result-qa', html);
  } catch (err) {
    showError('result-qa', err);
  }
});

// ── Azure OpenAI - Generate ──────────────────────────────────

document.getElementById('form-generate').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-generate');
  try {
    const fd = new FormData(e.target);
    const body = {
      document_type: fd.get('document_type'),
      instructions: fd.get('instructions'),
      language: fd.get('language'),
      max_tokens: 2000,
    };
    const data = await postJson('/analysis/generate', body);

    const rendered = renderMarkdown(data.document || '');
    document.getElementById('result-generate').className = 'result-area markdown-preview';
    document.getElementById('result-generate').innerHTML = rendered;
  } catch (err) {
    showError('result-generate', err);
  }
});

// ── Azure OpenAI - Classify ──────────────────────────────────

document.getElementById('form-classify').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-classify');
  try {
    const fd = new FormData(e.target);
    const data = await postJson('/analysis/classify', { text: fd.get('text') });

    let html = '';
    if (data.type) html += resultBlock('Type de document', `<span class="tag">${data.type}</span>`);
    if (data.domain) html += resultBlock('Domaine', `<span class="tag">${data.domain}</span>`);
    if (data.language) html += resultBlock('Langue', `<span class="tag">${data.language}</span>`);
    if (data.formality) html += resultBlock('Formalité', data.formality);
    if (data.confidentiality) html += resultBlock('Confidentialité', data.confidentiality);
    if (data.topics?.length) html += resultBlock('Sujets principaux', tagList(data.topics));

    showResult('result-classify', html || jsonBlock(data));
  } catch (err) {
    showError('result-classify', err);
  }
});

// ── Computer Vision ──────────────────────────────────────────

document.querySelector('input[name="file"][accept*=".png"]').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    const preview = document.getElementById('vision-preview');
    preview.innerHTML = `<img src="${ev.target.result}" alt="preview" />`;
  };
  reader.readAsDataURL(file);
});

document.getElementById('form-vision').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-vision');
  try {
    const fd = new FormData(e.target);
    const features = Array.from(e.target.querySelectorAll('input[name="features"]:checked'))
      .map(cb => cb.value).join(',');
    fd.set('features', features);
    const data = await postForm('/documents/vision-analyze', fd);

    let html = '';
    if (data.caption) {
      html += resultBlock('Légende',
        `<em style="font-size:1rem">"${escapeHtml(data.caption)}"</em>
         <span style="color:var(--text-muted)"> (${(data.caption_confidence*100).toFixed(0)}% de confiance)</span>`);
    }
    if (data.tags?.length) {
      html += resultBlock('Tags', tagList(data.tags.map(t => `${t.name} (${(t.confidence*100).toFixed(0)}%)`)));
    }
    if (data.objects?.length) {
      html += resultBlock('Objets détectés', tagList(data.objects.map(o => o.name)));
    }
    if (data.extracted_text) {
      html += resultBlock('Texte OCR extrait', `<pre>${escapeHtml(data.extracted_text.substring(0, 600))}</pre>`);
    }
    if (data.dense_captions?.length) {
      html += resultBlock('Légendes détaillées', data.dense_captions.slice(0,5).map(dc =>
        `<div style="padding:.25rem 0;border-bottom:1px solid var(--border)">${escapeHtml(dc.text)}</div>`
      ).join(''));
    }
    if (data.people?.length) {
      html += resultBlock('Personnes détectées', `${data.people.length} personne(s)`);
    }

    showResult('result-vision', html || jsonBlock(data));
  } catch (err) {
    showError('result-vision', err);
  }
});

// ── Translator ───────────────────────────────────────────────

document.getElementById('form-translate').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-translate');
  try {
    const fd = new FormData(e.target);
    const targets = Array.from(e.target.querySelectorAll('input[name="targets"]:checked')).map(cb => cb.value);
    if (!targets.length) { toast('Sélectionnez au moins une langue cible.', 'error'); return; }

    const body = {
      text: fd.get('text'),
      target_languages: targets,
    };
    const data = await postJson('/analysis/translate', body);

    let html = resultBlock('Langue source détectée',
      `<strong>${data.source_language}</strong> (confiance: ${(data.source_language_confidence*100).toFixed(0)}%)`);

    data.translations?.forEach(t => {
      html += resultBlock(t.target_language.toUpperCase(),
        `<blockquote style="border-left:3px solid var(--azure-blue);padding:.5rem 1rem;background:var(--bg);border-radius:0 6px 6px 0">
          ${escapeHtml(t.translated_text)}
        </blockquote>`);
    });

    showResult('result-translate', html);
  } catch (err) {
    showError('result-translate', err);
  }
});

// ── Content Safety ────────────────────────────────────────────

document.getElementById('form-safety').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-safety');
  try {
    const fd = new FormData(e.target);
    const body = { text: fd.get('text') };
    const data = await postJson('/analysis/safety', body);

    const statusCls = data.is_safe ? 'safety-ok' : 'safety-danger';
    const statusText = data.is_safe ? 'CONTENU SUR' : 'CONTENU BLOQUE';

    let html = `<div style="font-size:1.2rem;margin-bottom:1rem" class="${statusCls}">
      ${data.is_safe ? '✅' : '🚫'} ${statusText}
    </div>`;

    if (data.blocked_reason) {
      html += `<div style="color:var(--danger);margin-bottom:1rem">${escapeHtml(data.blocked_reason)}</div>`;
    }

    data.categories?.forEach(cat => {
      const sevClass = `severity-${cat.severity}`;
      html += `<div style="display:flex;align-items:center;gap:.75rem;padding:.4rem 0;border-bottom:1px solid var(--border)">
        <div style="width:100px;font-weight:500">${cat.category}</div>
        <span class="severity-badge ${sevClass}">Sévérité ${cat.severity}</span>
        ${cat.filtered ? '<span style="color:var(--danger);font-size:.8rem">BLOQUE</span>' : '<span style="color:var(--success);font-size:.8rem">OK</span>'}
      </div>`;
    });

    showResult('result-safety', html);
  } catch (err) {
    showError('result-safety', err);
  }
});

// ── AI Search ────────────────────────────────────────────────

document.getElementById('form-search').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-search');
  try {
    const fd = new FormData(e.target);
    const body = {
      query: fd.get('query'),
      semantic_search: fd.get('semantic') === 'on',
      top: parseInt(fd.get('top') || '5'),
    };
    const data = await postJson('/search/query', body);

    let html = resultBlock('Résultats', `${data.total_count} document(s) trouvé(s) pour "${escapeHtml(data.query)}"`);

    if (!data.results?.length) {
      html += '<div style="color:var(--text-muted);padding:1rem">Aucun résultat trouvé.</div>';
    } else {
      data.results.forEach((r, i) => {
        html += `<div style="border:1px solid var(--border);border-radius:8px;padding:1rem;margin-top:.75rem">
          <div style="display:flex;justify-content:space-between;align-items:start">
            <strong>${escapeHtml(r.title)}</strong>
            <span class="tag">Score: ${r.score.toFixed(2)}</span>
          </div>
          <div style="color:var(--text-muted);font-size:.8rem;margin:.25rem 0">${escapeHtml(r.document_id)}</div>
          <div style="font-size:.85rem;margin-top:.4rem">${escapeHtml(r.content_snippet)}...</div>
        </div>`;
      });
    }

    showResult('result-search', html);
  } catch (err) {
    showError('result-search', err);
  }
});

document.getElementById('form-index').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-index');
  try {
    const fd = new FormData(e.target);
    const body = {
      document_id: fd.get('document_id'),
      title: fd.get('title'),
      content: fd.get('content'),
      language: fd.get('language'),
      metadata: {},
    };
    const data = await postJson('/search/index/document', body);

    let html = '';
    if (data.succeeded) {
      html = `<div class="safety-ok">✅ Document indexé avec succès</div>` +
        resultBlock('Clé', `<code>${data.key}</code>`);
    } else {
      html = `<div class="safety-danger">❌ Échec de l'indexation</div>` + jsonBlock(data);
    }
    showResult('result-index', html);
  } catch (err) {
    showError('result-index', err);
  }
});

// ── Pipeline complet ─────────────────────────────────────────

document.getElementById('form-pipeline').addEventListener('submit', async (e) => {
  e.preventDefault();
  showLoading('result-pipeline');
  try {
    const fd = new FormData(e.target);
    // FormData doesn't send unchecked checkboxes
    ['run_nlp', 'run_classification', 'run_safety', 'run_summary'].forEach(key => {
      if (!fd.has(key)) fd.set(key, 'false');
    });

    const data = await postForm('/analysis/analyze-file', fd);

    let html = '';

    html += resultBlock('Fichier', data.filename);
    html += resultBlock('Longueur du texte extrait', `${data.extracted_text_length} caractères`);
    html += resultBlock('Aperçu du texte',
      `<pre style="max-height:120px">${escapeHtml(data.extracted_text_preview)}</pre>`);

    if (data.nlp) {
      const nlp = data.nlp;
      html += `<div style="background:var(--azure-blue-light);border-radius:8px;padding:1rem;margin:.75rem 0">
        <strong>Analyse NLP</strong><br>
        Langue: <strong>${nlp.detected_language || 'N/A'}</strong> |
        Sentiment: <strong>${nlp.sentiment || 'N/A'}</strong> |
        Entités: ${nlp.entities_count}<br>
        Phrases clés: ${tagList(nlp.key_phrases || [])}
        ${nlp.top_entities?.length ? `<br>Top entités: ${nlp.top_entities.map(e => `<span class="entity-pill">${escapeHtml(e.text)} <span style="opacity:.7">${e.category}</span></span>`).join('')}` : ''}
      </div>`;
    }

    if (data.classification) {
      const c = data.classification;
      html += `<div style="background:#EDE7F6;border-radius:8px;padding:1rem;margin:.75rem 0">
        <strong>Classification</strong><br>
        Type: <span class="tag">${c.type || 'N/A'}</span>
        Domaine: <span class="tag">${c.domain || 'N/A'}</span>
        Formalité: ${c.formality || 'N/A'}
        ${c.topics?.length ? `<br>Sujets: ${tagList(c.topics)}` : ''}
      </div>`;
    }

    if (data.content_safety) {
      const cs = data.content_safety;
      const safeClass = cs.is_safe ? 'safety-ok' : 'safety-danger';
      html += `<div style="background:${cs.is_safe ? '#D5F0D5' : '#FFEBEE'};border-radius:8px;padding:1rem;margin:.75rem 0">
        <strong class="${safeClass}">Sécurité: ${cs.is_safe ? '✅ Contenu sûr' : '🚫 Contenu bloqué'}</strong>
        ${cs.blocked_reason ? `<br><span style="color:var(--danger)">${escapeHtml(cs.blocked_reason)}</span>` : ''}
      </div>`;
    }

    if (data.summary) {
      const summ = data.summary;
      if (summ.abstractive) {
        html += resultBlock('Résumé (abstractif)',
          `<blockquote style="border-left:3px solid var(--azure-blue);padding:.5rem 1rem;background:var(--bg);border-radius:0 6px 6px 0">
            ${escapeHtml(summ.abstractive)}
          </blockquote>`);
      }
    }

    showResult('result-pipeline', html);
    toast('Pipeline terminé avec succès!', 'success');
  } catch (err) {
    showError('result-pipeline', err);
  }
});
