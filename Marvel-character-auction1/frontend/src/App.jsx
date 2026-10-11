import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './services/api';
import CharacterArt from './components/CharacterArt';
import TeamPanel from './components/TeamPanel';
import ResultsPanel from './components/ResultsPanel';
import './styles/global.css';

function Brand({ compact = false }) {
  return <div className={`brand ${compact ? 'brand--compact' : ''}`}><div className="brand-mark"><span>M</span><i>✦</i></div><div className="brand-copy"><strong>MARVEL <em>AUCTION</em></strong><small>CHARACTER BATTLE PROTOCOL</small></div></div>;
}

function Eyebrow({ children }) { return <span className="eyebrow">{children}</span>; }

function HomeScreen({ onCreate, onHistory, liveAI, catalogCount, busy }) {
  const [team1Name, setTeam1Name] = useState('The Avengers');
  const [team2Name, setTeam2Name] = useState('The Multiverse');
  const [universe, setUniverse] = useState('mixed');
  const [equipment, setEquipment] = useState('standard');
  const [showRules, setShowRules] = useState(false);
  const submit = (e) => { e.preventDefault(); onCreate({ team1_name: team1Name.trim() || 'The Avengers', team2_name: team2Name.trim() || 'The Multiverse', battle_universe: universe, equipment_mode: equipment }); };
  return (
    <main className="home-screen fade-in">
      <div className="hero-copy">
        <div className="status-row"><span className="live-dot" /> TACTICAL AUCTION SYSTEM <span className="status-divider" /> <span className={liveAI ? 'ai-state ai-state--live' : 'ai-state'}>{liveAI ? 'AI CONFIGURED' : 'OFFLINE PLAY ENABLED'}</span></div>
        <h1>BUILD YOUR<br /> <span>LEGENDARY</span><br />ROSTER.</h1>
        <p className="hero-subtitle">A cinematic character auction where every credit matters. Draft six legends. Outsmart your rival. Let the battle analyst decide who takes the multiverse.</p>
        <div className="hero-stats">
          <div><strong>$30</strong><small>TEAM BUDGET</small></div><div><strong>06</strong><small>ROSTER SLOTS</small></div><div><strong>20<span>s</span></strong><small>PER AUCTION</small></div>
        </div>
        <div className="hero-buttons"><button className="button button--gold button--large" onClick={() => document.getElementById('match-setup')?.scrollIntoView({ behavior: 'smooth' })}>START AUCTION <span>↗</span></button><button className="button button--ghost" onClick={onHistory}>MATCH ARCHIVE ↗</button></div>
      </div>
      <div className="hero-art-wrap" aria-hidden="true">
        <div className="hero-sunburst" /><div className="hero-ring hero-ring--one" /><div className="hero-ring hero-ring--two" />
        <div className="hero-silhouette hero-silhouette--one">✦</div><div className="hero-silhouette hero-silhouette--two">⚡</div>
        <div className="hero-art-card"><span className="card-orbit card-orbit--a" /><span className="card-orbit card-orbit--b" /><div className="hero-art-logo">M</div><div className="hero-art-caption"><Eyebrow>THE ARENA IS YOURS</Eyebrow><strong>WHO WILL<br />YOU DRAFT?</strong></div><div className="hero-card-number">LOCAL — VARIANT POOL</div></div>
        <div className="floating-chip floating-chip--left"><span>✦</span> TACTICAL DRAFTING</div><div className="floating-chip floating-chip--right"><span>⚡</span> POWER ISN'T EVERYTHING</div>
      </div>
      <section className="setup-grid" id="match-setup">
        <div className="setup-intro"><Eyebrow>01 / CONFIGURE YOUR ARENA</Eyebrow><h2>THE NEXT LEGEND<br /><span>IS UP FOR GRABS.</span></h2><p>Name your squads, pick the battle rules, then compete for characters from Marvel movie continuities.</p><div className="catalog-counter"><span className="catalog-pip" /><div><strong>{catalogCount ? `${catalogCount} CHARACTER VARIANTS` : 'CHARACTER CATALOG'}</strong><small>Local fallback pool · More than one continuity</small></div></div></div>
        <form className="setup-card card-surface" onSubmit={submit}>
          <div className="setup-card__title"><div><Eyebrow>NEW MATCH</Eyebrow><h3>Set your teams</h3></div><span className="setup-icon">✦</span></div>
          <label className="field-label" htmlFor="team1">TEAM 01 <small>RED CORNER</small></label><input id="team1" maxLength={80} value={team1Name} onChange={(e) => setTeam1Name(e.target.value)} placeholder="Team name" />
          <label className="field-label" htmlFor="team2">TEAM 02 <small>GOLD CORNER</small></label><input id="team2" maxLength={80} value={team2Name} onChange={(e) => setTeam2Name(e.target.value)} placeholder="Team name" />
          <div className="form-two-col"><div><label className="field-label" htmlFor="universe">BATTLE UNIVERSE</label><select id="universe" value={universe} onChange={(e) => setUniverse(e.target.value)}><option value="mixed">Mixed Marvel movies</option><option value="mcu">MCU only</option></select></div><div><label className="field-label" htmlFor="equipment">EQUIPMENT</label><select id="equipment" value={equipment} onChange={(e) => setEquipment(e.target.value)}><option value="standard">Standard</option><option value="peak">Peak demonstrated</option></select></div></div>
          <div className="rules-summary"><span>RULESET LOCKED</span><p><b>$30</b> budget <i /> <b>6</b> characters <i /> <b>2</b> skips <i /> <b>20s</b> timer</p><button type="button" className="text-button" onClick={() => setShowRules(!showRules)}>{showRules ? 'Hide rules −' : 'View rules +'}</button>{showRules && <ul><li>First bid opens at the character's starting bid. Later bids rise by exactly $1.</li><li>One skip token is spent when a team passes; the same team cannot pass twice in one round.</li><li>The server's clock controls expiry, and the highest valid bid wins.</li><li>Match ends at full rosters or when no eligible auction is possible. You can also end it manually.</li></ul>}</div>
          <button className="button button--gold button--full" type="submit" disabled={busy}>{busy ? 'OPENING ARENA…' : 'INITIALIZE MATCH'} <span>→</span></button>
          <div className="setup-footnote"><span className="lock-icon">▣</span> All bids and budgets validated server-side.</div>
        </form>
      </section>
      <section className="feature-row"><div className="feature-cell"><span>01</span><div><strong>LIVE CHARACTER DRAFT</strong><p>Unique character variants, timed bidding, and a persistent budget ledger.</p></div></div><div className="feature-cell"><span>02</span><div><strong>AI BATTLE INTELLIGENCE</strong><p>Compare feats, counters, power synergy, durability, and tactical control.</p></div></div><div className="feature-cell"><span>03</span><div><strong>LOCAL-FIRST GAMEPLAY</strong><p>Play offline with SQLite. Configure an API key only for live AI analysis.</p></div></div></section>
    </main>
  );
}

function AuctionScreen({ match, busy, onBid, onSkip, onNext, onEnd, onHistory, onAnalyze, analyzing }) {
  const auction = match.auction;
  const character = auction?.character;
  const [now, setNow] = useState(Date.now());
  const [clockSync, setClockSync] = useState({ auctionId: auction?.id, seconds: auction?.seconds_remaining || 0, receivedAt: Date.now() });
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 100); return () => clearInterval(id); }, []);
  useEffect(() => { setClockSync({ auctionId: auction?.id, seconds: auction?.seconds_remaining || 0, receivedAt: Date.now() }); }, [auction?.id, auction?.status, auction?.seconds_remaining]);
  const elapsedSinceServerSync = Math.max(0, (now - clockSync.receivedAt) / 1000);
  const remaining = auction?.status === 'active' ? Math.max(0, Math.ceil((clockSync.auctionId === auction.id ? clockSync.seconds : auction.seconds_remaining || 0) - elapsedSinceServerSync)) : 0;
  const total = match.auction_duration_seconds || 20;
  const progress = Math.max(0, Math.min(100, remaining / total * 100));
  const active = auction?.status === 'active';
  const [showDetails, setShowDetails] = useState(false);
  useEffect(() => setShowDetails(false), [character?.id]);
  const leaderTeam = match.teams.find((team) => team.id === auction?.leading_team_id);
  const nextAmount = auction?.leading_team_id ? auction.current_bid + 1 : auction?.starting_bid;
  return (
    <main className="game-screen fade-in">
      <div className="game-topbar"><div className="game-match-meta"><span className="live-dot" /><Eyebrow>{active ? 'AUCTION LIVE' : 'ROUND COMPLETE'}</Eyebrow><span className="meta-divider" /> MATCH {match.id.slice(0, 8).toUpperCase()} <span className="meta-divider" /> ROUND {match.round_number}</div><div className="topbar-actions"><span className="rule-pill">{match.battle_universe === 'mcu' ? 'MCU ONLY' : 'MIXED UNIVERSES'}</span><button className="text-button" onClick={onHistory}>ARCHIVE ↗</button><button className="text-button text-button--danger" onClick={onEnd} disabled={busy}>END MATCH</button></div></div>
      {active ? (
        <section className="auction-hero">
          <div className="auction-left"><div className="auction-round-label"><span>ROUND</span><strong>{String(auction.round_number).padStart(2, '0')}</strong><span className="round-line" /><span className="round-season">THE CHARACTER DROP</span></div>
            <div className="current-character"><CharacterArt character={character} size="large" /><div className="character-identity"><div className="character-tags"><span className={`class-tag class-tag--${(character.classification || '').toLowerCase().replace(/[^a-z]+/g, '-')}`}>{character.classification}</span><span className="universe-tag">{character.universe}</span><span className={`selection-tag ${auction.selection_source === 'ai-selected' ? 'selection-tag--ai' : ''}`}>{auction.selection_source === 'ai-selected' ? 'AI PICK' : 'LOCAL CATALOG'}</span></div><h1>{character.display_name}</h1><h2>{character.identity}</h2><p className="alias-line">{character.alias}</p><div className="movie-line"><span className="movie-icon">▣</span><div><small>FIRST RELEVANT FILM</small><strong>{character.first_movie}</strong></div></div><div className="power-chips">{(character.powers || []).slice(0, 4).map((power) => <span key={power}>{power}</span>)}</div><button className="text-button detail-toggle" onClick={() => setShowDetails(!showDetails)}>{showDetails ? 'HIDE FIELD INTEL −' : 'VIEW FIELD INTEL +'}</button>{showDetails && <div className="field-intel"><div><b>WEAKNESSES</b><ul>{(character.weaknesses || []).map((x) => <li key={x}>{x}</li>)}</ul></div><div><b>FILM FEATS</b><ul>{(character.feats || []).map((x) => <li key={x}>{x}</li>)}</ul></div><small>Source references are attached to the character profile where available.</small></div>}</div></div>
          </div>
          <div className="auction-right"><div className="timer-card card-surface"><div className="timer-card__head"><Eyebrow>TIME LEFT</Eyebrow><span className="server-badge"><span className="live-dot" /> SERVER CLOCK</span></div><div className={`timer-ring ${remaining <= 5 ? 'timer-ring--urgent' : ''}`} style={{ '--timer-progress': `${progress}%` }}><div className="timer-ring__inner"><strong>{String(remaining).padStart(2, '0')}</strong><span>SECONDS</span></div></div><div className="timer-progress"><span style={{ width: `${progress}%` }} /></div><div className="bid-stat-grid"><div><small>STARTING BID</small><strong>${auction.starting_bid}</strong></div><div><small>CURRENT BID</small><strong className="bid-current">${auction.current_bid || '—'}</strong></div></div><div className="leading-team"><span className="leading-icon">{leaderTeam ? '⚑' : '◈'}</span><div><small>{leaderTeam ? 'CURRENT HIGH BIDDER' : 'OPEN FLOOR'}</small><strong>{leaderTeam ? leaderTeam.name : 'No bids yet'}</strong></div><span className="bid-count">{auction.bid_count} {auction.bid_count === 1 ? 'BID' : 'BIDS'}</span></div>{leaderTeam && <div className="raise-hint">Next valid bid: <b>${nextAmount}</b></div>}{remaining === 0 && <button className="button button--gold button--full resolve-button" disabled={busy} onClick={onResolve}>RESOLVE AUCTION →</button>}</div>
            <div className="auction-rule-note"><span>✦</span><p>Each bid is validated by the server. Refreshing this page won't reset the clock.</p></div>
          </div>
        </section>
      ) : (
        <section className="round-result card-surface"><div className={`round-result__stamp round-result__stamp--${(auction?.result || 'no-bids').toLowerCase().replace('_','-')}`}>{auction?.result === 'SOLD' ? 'SOLD' : auction?.result === 'PASSED' ? 'PASSED' : 'NO BIDS'}</div><div className="round-result__copy"><Eyebrow>ROUND {String(auction?.round_number || match.round_number).padStart(2, '0')} CLOSED</Eyebrow><h2>{auction?.result === 'SOLD' ? `${auction.winner_team_name} secured ${character?.display_name}.` : auction?.result === 'PASSED' ? `${character?.display_name} passed out of the auction.` : `${character?.display_name} went unsold.`}</h2><p>{auction?.result === 'SOLD' ? `Winning bid: $${auction.current_bid}. The team's remaining budget has been updated.` : 'No budget was charged for this round.'}</p></div>{match.status === 'auctioning' ? <button className="button button--gold" onClick={() => onNext(false)} disabled={busy}>NEXT CHARACTER →</button> : <button className="button button--gold" onClick={onAnalyze} disabled={busy || analyzing}>{analyzing ? 'ANALYZING…' : 'RUN BATTLE ANALYSIS →'}</button>}</section>
      )}
      <div className="teams-heading"><div><Eyebrow>THE CONTENDERS</Eyebrow><h2>BUILD A BETTER <span>TEAM.</span></h2></div><div className="team-legend"><span><i className="legend-dot legend-dot--red" /> TEAM 01</span><span><i className="legend-dot legend-dot--gold" /> TEAM 02</span></div></div>
      <section className="teams-grid">{match.teams.map((team) => <TeamPanel key={team.id} team={team} active={auction?.leading_team_id === team.id} disabled={!active || remaining === 0 || match.status !== 'auctioning'} auction={auction} onBid={onBid} onSkip={onSkip} busy={busy} />)}</section>
      {match.status === 'completed' && <div className="complete-match-cta card-surface"><div><Eyebrow>AUCTION CONCLUDED</Eyebrow><h3>Your rosters are locked. Let the battle analyst weigh in.</h3><p>{match.end_reason}</p></div><button className="button button--gold" onClick={onAnalyze} disabled={busy || analyzing}>{analyzing ? 'ANALYZING…' : 'ANALYZE TEAMS →'}</button></div>}
      <footer className="game-footer"><Brand compact /><p>HYPOTHETICAL BATTLE SIMULATION · NOT CANONICAL MARVEL OUTCOMES</p><button className="text-button" onClick={onHistory}>MATCH ARCHIVE ↗</button></footer>
    </main>
  );
}

function HistoryModal({ open, loading, results, onClose, onOpenMatch }) {
  if (!open) return null;
  return <div className="modal-backdrop" role="presentation" onClick={onClose}><section className="history-modal card-surface" role="dialog" aria-modal="true" aria-labelledby="history-title" onClick={(e) => e.stopPropagation()}><div className="modal-head"><div><Eyebrow>ARCHIVE / SAVED MATCHES</Eyebrow><h2 id="history-title">Battle history</h2></div><button className="close-button" onClick={onClose} aria-label="Close">×</button></div>{loading ? <div className="history-empty">Loading saved matches…</div> : results.length === 0 ? <div className="history-empty"><span>◈</span><h3>No completed matches yet.</h3><p>Finish an auction to save a result here.</p></div> : <div className="history-list">{results.map((item) => { const analysis = item.analysis?.analysis; const winner = analysis && item.teams.find((t) => t.id === analysis.winner_team_id); return <button className="history-item" key={item.id} onClick={() => onOpenMatch(item.id)}><div className="history-item__round"><strong>{String(item.round_number).padStart(2,'0')}</strong><small>ROUNDS</small></div><div className="history-item__main"><strong>{item.teams?.[0]?.name || 'Team 1'} <i>VS</i> {item.teams?.[1]?.name || 'Team 2'}</strong><small>{item.completed_at ? new Date(item.completed_at).toLocaleString() : 'Saved match'} · {item.id.slice(0,8).toUpperCase()}</small><span>{winner ? `Predicted winner: ${winner.name}` : 'Battle analysis not generated yet'}</span></div><div className="history-arrow">↗</div></button>; })}</div>}<div className="modal-footer"><span>Last 30 completed matches saved locally.</span><button className="button button--ghost" onClick={onClose}>CLOSE</button></div></section></div>;
}

function Toast({ message, kind = 'error', onClose }) {
  if (!message) return null;
  return <div className={`toast toast--${kind}`} role="status"><span>{kind === 'error' ? '!' : '✓'}</span><p>{message}</p><button onClick={onClose} aria-label="Dismiss">×</button></div>;
}

export default function App() {
  const [match, setMatch] = useState(null);
  const [health, setHealth] = useState({ live_ai_available: false, catalog_count: 0 });
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [toast, setToast] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const showError = useCallback((message) => { setToast({ message, kind: 'error' }); window.setTimeout(() => setToast(null), 6000); }, []);
  const showNotice = useCallback((message) => { setToast({ message, kind: 'success' }); window.setTimeout(() => setToast(null), 3800); }, []);

  useEffect(() => { api.health().then(setHealth).catch(() => setHealth({ live_ai_available: false, catalog_count: 0 })); }, []);

  useEffect(() => {
    if (!match?.id || match.status === 'completed') return undefined;
    let alive = true;
    let timer;
    const poll = async () => {
      try {
        const latest = await api.getMatch(match.id);
        if (alive) setMatch(latest);
      } catch (error) {
        if (alive && !/not found/i.test(error.message)) console.warn('State polling failed:', error.message);
      } finally {
        if (alive) timer = window.setTimeout(poll, 900);
      }
    };
    timer = window.setTimeout(poll, 900);
    return () => { alive = false; window.clearTimeout(timer); };
  }, [match?.id, match?.status]);

  const runAction = useCallback(async (action, successMessage) => {
    if (busy) return;
    setBusy(true); setToast(null);
    try {
      const updated = await action();
      if (updated && updated.teams) setMatch(updated);
      else if (match?.id) setMatch(await api.getMatch(match.id));
      if (successMessage) showNotice(successMessage);
    } catch (error) {
      showError(error.message || 'Something went wrong.');
      if (match?.id) { try { setMatch(await api.getMatch(match.id)); } catch {} }
    } finally { setBusy(false); }
  }, [busy, match?.id, showError, showNotice]);

  const startMatch = async (payload) => {
    if (busy) return;
    setBusy(true); setToast(null);
    try {
      const created = await api.createMatch(payload);
      setMatch(created);
      showNotice('Arena initialized. Your first character is on the block.');
    } catch (error) { showError(error.message || 'Could not start match.'); }
    finally { setBusy(false); }
  };

  const openHistory = async () => {
    setHistoryOpen(true); setHistoryLoading(true);
    try { const response = await api.history(); setHistory(response.results || []); }
    catch (error) { showError(error.message); setHistory([]); }
    finally { setHistoryLoading(false); }
  };

  const openSavedMatch = async (id) => {
    setBusy(true);
    try { const saved = await api.result(id); setMatch(saved); setHistoryOpen(false); }
    catch (error) { showError(error.message); }
    finally { setBusy(false); }
  };

  const doAnalyze = async () => {
    if (!match?.id || analyzing) return;
    setAnalyzing(true); setToast(null);
    try {
      await api.analyze(match.id);
      setMatch(await api.getMatch(match.id));
      const updated = await api.getMatch(match.id);
      if (updated.battle_analysis?.provider === 'local-fallback') showNotice('Fallback analysis saved. Live AI is not configured or unavailable.');
      else showNotice('Battle analysis complete and saved.');
    } catch (error) { showError(error.message || 'Battle analysis could not be generated.'); }
    finally { setAnalyzing(false); }
  };

  const current = match?.auction;
  const completed = match?.status === 'completed';
  return (
    <div className="app-shell">
      <div className="ambient ambient--one" /><div className="ambient ambient--two" />
      <header className="site-header"><button className="brand-button" onClick={() => setMatch(null)} aria-label="Return home"><Brand /></button><nav><a href="#rules" onClick={(e) => { e.preventDefault(); if (!match) document.getElementById('match-setup')?.scrollIntoView({ behavior: 'smooth' }); else showNotice('Rules: $30 budgets, 6 slots, 2 skips, 20 seconds per auction.'); }}>RULES</a><button onClick={openHistory}>MATCH ARCHIVE</button><span className={`nav-ai ${health.live_ai_available ? 'nav-ai--live' : ''}`}><i /> {health.live_ai_available ? 'AI CONFIGURED' : 'LOCAL MODE'}</span></nav></header>
      {!match ? <HomeScreen onCreate={startMatch} onHistory={openHistory} liveAI={health.live_ai_available} catalogCount={health.catalog_count} busy={busy} /> : completed ? <ResultsPanel match={match} onPlayAgain={() => setMatch(null)} onHistory={openHistory} onAnalyze={doAnalyze} analyzing={analyzing} busy={busy} /> : <AuctionScreen match={match} busy={busy} onBid={(teamId) => runAction(() => api.bid(current.id, teamId))} onSkip={(teamId) => runAction(() => api.skip(current.id, teamId), 'Skip registered. One token was used.')} onNext={() => runAction(() => api.nextCharacter(match.id))} onResolve={() => runAction(() => api.resolve(current.id))} onEnd={() => { if (window.confirm('End this match now? Any current valid high bid will be resolved, then the rosters will be locked.')) runAction(() => api.endMatch(match.id)); }} onHistory={openHistory} onAnalyze={doAnalyze} analyzing={analyzing} />}
      <HistoryModal open={historyOpen} loading={historyLoading} results={history} onClose={() => setHistoryOpen(false)} onOpenMatch={openSavedMatch} />
      <Toast message={toast?.message} kind={toast?.kind} onClose={() => setToast(null)} />
      <div className="bottom-legal">MARVEL CHARACTER AUCTION BATTLE <span>·</span> FAN-MADE HYPOTHETICAL GAME <span>·</span> NOT AFFILIATED WITH MARVEL</div>
    </div>
  );
}
