// Load data from summary.json symlink or param
async function loadData() {
  try {
    const res = await fetch('data.json');
    return await res.json();
  } catch {
    document.body.innerHTML = '&lt;p&gt;No data.json. Run ./run_suite.sh --dashboard&lt;/p&gt;';
  }
}

function renderProfiles(data) {
  const profiles = document.getElementById('profiles');
  profiles.innerHTML = `
    &lt;div class=&quot;card&quot;&gt;&lt;h2&gt;Profile&lt;/h2&gt;&lt;p&gt;${data.profile}&lt;/p&gt;&lt;/div&gt;
    &lt;div class=&quot;card&quot;&gt;&lt;h2&gt;Interpreter&lt;/h2&gt;&lt;p&gt;${data.suite_interpreter}&lt;/p&gt;&lt;/div&gt;
    &lt;div class=&quot;card&quot;&gt;&lt;h2&gt;Categories&lt;/h2&gt;&lt;p&gt;${data.selected_categories.join(', ')}&lt;/p&gt;&lt;/div&gt;
  `;
}

function renderResults(data) {
  const canvas = document.getElementById('rChart');
  const ctx = canvas.getContext('2d');
  const labels = Object.keys(data.results || {});
  const scores = labels.map(k => data.results[k].score || 0);
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Score', data: scores, backgroundColor: 'linear-gradient(45deg, gold, orange)' }]
    },
    options: { scales: { y: { beginAtZero: true } } }
  });
}

function renderGraphics(data) {
  const canvas = document.getElementById('gChart');
  const ctx = canvas.getContext('2d');
  const gpuData = data.results.gpu_game || {};
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['FPS', 'Frame Time'],
      datasets: [{ label: 'GPU Game', data: [gpuData.fps, gpuData.frametime_ms], borderColor: 'cyan' }]
    }
  });
}

function showTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.style.display = 'none');
  document.getElementById(tab).style.display = 'block';
}

loadData().then(data => {
  renderProfiles(data);
  renderResults(data);
  renderGraphics(data);
  showTab('profiles');
});
