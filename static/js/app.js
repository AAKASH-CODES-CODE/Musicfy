/* =============================================
   MUSICFY — Main Application Script
   ============================================= */

const $ = id => document.getElementById(id);

// ── Tab Switching ──────────────────────────────
function switchTab(targetPageId, clickedEl) {
  document.querySelectorAll('.page-section').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById(targetPageId).classList.add('active');
  clickedEl.classList.add('active');
  $('main-header').style.display = targetPageId === 'home-page' ? 'flex' : 'none';
  if (targetPageId === 'library-page') loadLibrary();
}

// ── Format Duration ────────────────────────────
function formatDuration(ms) {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, '0')}`;
}

// ── Format big numbers ─────────────────────────
function formatCount(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K';
  return n;
}

// ── Skeleton HTML ──────────────────────────────
function skeletonList(count = 4) {
  return Array.from({ length: count }, () => `
    <div class="list-item skeleton-item">
      <div class="skeleton skeleton-thumb"></div>
      <div class="item-info">
        <div class="skeleton skeleton-line wide"></div>
        <div class="skeleton skeleton-line narrow"></div>
      </div>
    </div>`).join('');
}

function skeletonCards(count = 4) {
  return Array.from({ length: count }, () => `
    <div class="scroll-card">
      <div class="skeleton skeleton-card-img"></div>
      <div class="skeleton skeleton-line wide" style="margin-top:8px;"></div>
      <div class="skeleton skeleton-line narrow"></div>
    </div>`).join('');
}

// ── Track list item HTML ───────────────────────
function trackListItem(track, index) {
  const dur = track.duration_ms ? formatDuration(track.duration_ms) : '';
  // Title aur artist me quotes handle karne ke liye
  const safeTitle = (track.title || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
  const safeArtist = (track.artist || '').replace(/'/g, "\\'").replace(/"/g, '\\"');

  return `
    <div class="list-item" onclick="playSong('${track.id}', '${safeTitle}', '${safeArtist}', '${track.thumb}')">
      <div class="track-num">${index + 1}</div>
      <img src="${track.thumb || 'https://placehold.co/55x55/242424/a7a7a7?text=♪'}"
           alt="Cover" class="track-thumb" loading="lazy"
           onerror="this.src='https://placehold.co/55x55/242424/a7a7a7?text=♪'">
      <div class="item-info">
        <div class="item-title">${track.title}</div>
        <div class="item-subtitle">${track.artist}</div>
      </div>
      ${dur ? `<span class="track-dur">${dur}</span>` : ''}
      <button class="options-btn" aria-label="Options"><i class="fas fa-ellipsis-v"></i></button>
    </div>`;
}

// ── Scroll card HTML ───────────────────────────
function scrollCard(item) {
  const sub = item.artist || item.owner || '';
  
  // Quotes handle karne ke liye
  const safeTitle = (item.title || item.name || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
  const safeArtist = (item.artist || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
  
  // Agar item me artist hai (matlab song hai), tabhi click par play hoga
  const clickAction = item.artist ? `onclick="playSong('${item.id}', '${safeTitle}', '${safeArtist}', '${item.thumb}')"` : '';

  return `
    <div class="scroll-card" ${clickAction}>
      <div class="card-img-wrap">
        <img src="${item.thumb || 'https://placehold.co/150x150/242424/a7a7a7?text=♪'}"
             alt="${safeTitle}" loading="lazy"
             onerror="this.src='https://placehold.co/150x150/242424/a7a7a7?text=♪'">
        ${item.artist ? `<div class="card-play-btn"><i class="fas fa-play"></i></div>` : ''}
      </div>
      <div class="card-title">${item.title || item.name}</div>
      ${sub ? `<div class="card-sub">${sub}</div>` : ''}
    </div>`;
}

// ── HOME: fetch all home data ──────────────────
async function fetchHomeMusic() {
  $('api-start-listening').innerHTML = skeletonList(5);
  $('api-recommended').innerHTML = skeletonCards(4);
  $('api-trending').innerHTML = skeletonList(4);

  try {
    const res = await fetch('/api/home_music');
    const data = await res.json();

    if (!data.success) {
      $('api-start-listening').innerHTML = '<p class="error-msg">Could not load music. Check your Spotify credentials.</p>';
      return;
    }

    // New Releases (list)
    const slContainer = $('api-start-listening');
    if (data.start_listening?.length) {
      slContainer.innerHTML = data.start_listening
        .map((item, i) => trackListItem({ ...item, artist: item.artist }, i))
        .join('');
    } else {
      slContainer.innerHTML = '<p class="empty-msg">No releases found.</p>';
    }

    // Recommended (cards)
    const recContainer = $('api-recommended');
    if (data.recommended?.length) {
      recContainer.innerHTML = data.recommended.map(scrollCard).join('');
    } else {
      recContainer.innerHTML = '<p class="empty-msg">No playlists found.</p>';
    }

    // Trending (list)
    const trendContainer = $('api-trending');
    if (data.trending?.length) {
      trendContainer.innerHTML = data.trending.map((t, i) => trackListItem(t, i)).join('');
    } else {
      trendContainer.innerHTML = '<p class="empty-msg">No trending songs found.</p>';
    }

  } catch (err) {
    console.error('Home music error:', err);
    $('api-start-listening').innerHTML = '<p class="error-msg">Network error. Please refresh.</p>';
  }
}

// ── HOME: fetch personal user data ────────────
async function fetchUserMusic() {
  try {
    const [topRes, recentRes] = await Promise.all([
      fetch('/api/user_music'),
      fetch('/api/recent_tracks')
    ]);
    const topData = await topRes.json();
    const recentData = await recentRes.json();

    if (topData.success && topData.tracks.length) {
      $('spotify-user-section').style.display = 'block';
      $('api-user-tracks').innerHTML = topData.tracks.map(scrollCard).join('');
    }

    if (recentData.success && recentData.tracks.length) {
      $('recent-section').style.display = 'block';
      $('api-recent-tracks').innerHTML = recentData.tracks.map(scrollCard).join('');
    }
  } catch (err) {
    console.error('User music error:', err);
  }
}

// ── LIBRARY ─────────────────────────────────
async function loadLibrary() {
  const container = $('library-content');
  container.innerHTML = skeletonList(6);

  try {
    const res = await fetch('/api/saved_tracks');
    const data = await res.json();

    if (!data.success) {
      container.innerHTML = `
        <div class="library-empty">
          <i class="fas fa-heart" style="font-size:48px;color:#535353;margin-bottom:16px;"></i>
          <p>Connect your Spotify to see your saved songs</p>
          <a href="/login" class="btn-connect">Connect Spotify</a>
        </div>`;
      return;
    }

    if (!data.tracks.length) {
      container.innerHTML = '<div class="library-empty"><p>No saved songs yet. Like songs on Spotify to see them here.</p></div>';
      return;
    }

    container.innerHTML = data.tracks.map((t, i) => trackListItem(t, i)).join('');
  } catch (err) {
    container.innerHTML = '<p class="error-msg">Could not load library.</p>';
  }
}

// ── SEARCH ────────────────────────────────────
let searchTimeout = null;

function initSearch() {
  const input = $('main-search-input');
  const defaultUI = $('search-default-ui');
  const resultsUI = $('search-results-ui');
  const trackResults = $('live-search-results');
  const artistResults = $('artist-results');
  const artistSection = $('artist-section');

  if (!input) return;

  input.addEventListener('input', e => {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();

    if (!query) {
      defaultUI.style.display = 'block';
      resultsUI.style.display = 'none';
      return;
    }

    defaultUI.style.display = 'none';
    resultsUI.style.display = 'block';
    trackResults.innerHTML = skeletonList(5);
    artistResults.innerHTML = '';
    artistSection.style.display = 'none';

    searchTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        if (!data.success) {
          if (data.login_required) {
            trackResults.innerHTML = `
              <div class="login-prompt">
                <i class="fab fa-spotify"></i>
                <p>Please connect spotify to search</p>
                <a href="/login" class="btn-connect">Connect Spotify</a>
              </div>`;
          } else {
            trackResults.innerHTML = '<p class="error-msg">Search failed. Try again.</p>';
          }
          return;
        }

        // Tracks
        if (data.results?.length) {
          trackResults.innerHTML = data.results.map((t, i) => trackListItem(t, i)).join('');
        } else {
          trackResults.innerHTML = '<p class="empty-msg">No tracks found.</p>';
        }

        // Artists
        if (data.artists?.length) {
          artistSection.style.display = 'block';
          artistResults.innerHTML = data.artists.map(a => `
            <div class="artist-card" data-id="${a.id}">
              <div class="artist-img-wrap">
                <img src="${a.thumb || 'https://placehold.co/100x100/242424/a7a7a7?text=♪'}"
                     alt="${a.name}" loading="lazy"
                     onerror="this.src='https://placehold.co/100x100/242424/a7a7a7?text=♪'">
              </div>
              <div class="artist-name">${a.name}</div>
              <div class="artist-sub">Artist · ${formatCount(a.followers)} followers</div>
            </div>`).join('');
        }

      } catch (err) {
        trackResults.innerHTML = '<p class="error-msg">Network error. Try again.</p>';
      }
    }, 300);
  });
}

// ── Filter Pills ──────────────────────────────
function initFilterPills() {
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
    });
  });
}

// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchHomeMusic();
  fetchUserMusic();
  initSearch();
  initFilterPills();
});


// ── MUSIC PLAYER LOGIC ────────────────────────────
let currentAudio = new Audio();
let isPlaying = false;

function togglePlayer() {
  $('music-player').classList.toggle('active');
}

async function playSong(id, title, artist, thumb) {
  // Player ko upar laao aur details set karo
  $('music-player').classList.add('active');
  $('player-title').innerText = title;
  $('player-artist').innerText = artist;
  $('player-thumb').src = thumb;
  
  // Spinner chalu karo loading ke time
  $('play-icon').className = 'fas fa-spinner fa-spin';
  $('player-thumb').classList.remove('playing');

  try {
    // Ab request direct browser se API par nahi, balki humare apne Backend par jayegi
    const res = await fetch(`/api/get_audio?title=${encodeURIComponent(title)}&artist=${encodeURIComponent(artist)}`);
    const data = await res.json();

    if (data.success && data.audio_url) {
      currentAudio.src = data.audio_url;
      currentAudio.play();
      isPlaying = true;

      // Play icon aur spinning animation chalu
      $('play-icon').className = 'fas fa-pause';
      $('player-thumb').classList.add('playing');
    } else {
      alert("Oops! Gaana nahi mil paya.");
      $('play-icon').className = 'fas fa-play';
    }
  } catch (err) {
    console.error("Audio Fetch Error:", err);
    alert("Server Error: Please try again.");
    $('play-icon').className = 'fas fa-play';
  }
}


// Play/Pause Button Logic
function togglePlay() {
  if (!currentAudio.src) return;
  if (isPlaying) {
    currentAudio.pause();
    $('play-icon').className = 'fas fa-play';
    $('player-thumb').classList.remove('playing');
  } else {
    currentAudio.play();
    $('play-icon').className = 'fas fa-pause';
    $('player-thumb').classList.add('playing');
  }
  isPlaying = !isPlaying;
}

// Progress Bar Update Logic
currentAudio.addEventListener('timeupdate', () => {
  if (currentAudio.duration) {
    const progressPercent = (currentAudio.currentTime / currentAudio.duration) * 100;
    $('progress-bar').style.width = `${progressPercent}%`;
    
    // Time format update
    let currentMin = Math.floor(currentAudio.currentTime / 60);
    let currentSec = Math.floor(currentAudio.currentTime % 60);
    if(currentSec < 10) currentSec = `0${currentSec}`;
    $('current-time').innerText = `${currentMin}:${currentSec}`;

    let totalMin = Math.floor(currentAudio.duration / 60);
    let totalSec = Math.floor(currentAudio.duration % 60);
    if(totalSec < 10) totalSec = `0${totalSec}`;
    $('total-time').innerText = `${totalMin}:${totalSec}`;
  }
});
