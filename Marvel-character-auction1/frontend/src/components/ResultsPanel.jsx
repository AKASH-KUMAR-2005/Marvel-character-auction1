import React from 'react';
import CharacterArt from './CharacterArt';

export default function ResultsPanel({ match, onPlayAgain, onHistory, onAnalyze, analyzing, busy }) {
  const analysis = match?.battle_analysis?.analysis;
  const provider = match?.battle_analysis?.provider;
  const teams = match?.teams || [];
  const winner = analysis ? teams.find((team) => team.id === analysis.winner_team_id) : null;
  return (
    <main className="results-page fade-in">
      <div className="results-overline"><span className="red-line" /> POST-BATTLE INTELLIGENCE <span className="red-line" /></div>
      <div className="results-title-wrap">
        <p className="eyebrow">MATCH #{match.id.slice(0, 8).toUpperCase()} · {match.round_number} ROUNDS</p>
        <h1>THE <span>VERDICT</span></h1>
        <p className="results-subtitle">A hypothetical outcome based on the purchased rosters, screen feats, and selected battle rules.</p>
      </div>
      {!analysis ? (
        <div className="analysis-prompt card-surface">
          <div className="analysis-symbol">✦</div>
          <h2>Run Battle Analysis</h2>
          <p>The analyst will compare power, durability, control, synergy, counters, and the actual movie versions on both teams.</p>
          <button className="button button--gold" disabled={busy || analyzing} onClick={onAnalyze}>{analyzing ? 'ANALYZING ROSTERS…' : 'GENERATE BATTLE VERDICT'}</button>
          <small>Live AI is used only when an API key is configured. Otherwise the result is labeled as a local fallback.</small>
        </div>
      ) : (
        <>
          <section className="winner-banner card-surface">
            <div className="winner-corner">PREDICTED WINNER</div>
            <div className="winner-emblem">✦</div>
            <div className="winner-main"><span className="eyebrow">THE ANALYST FAVORS</span><h2>{winner?.name || 'No clear winner'}</h2><p>{analysis.likely_outcome}</p></div>
            <div className="winner-confidence"><span>CONFIDENCE</span><strong>{analysis.confidence?.toUpperCase()}</strong><small>{analysis.team1_win_probability}% — {analysis.team2_win_probability}%</small></div>
          </section>
          <section className="probability-section">
            <div className="section-heading"><div><span className="eyebrow">PREDICTED WIN PROBABILITY</span><h2>Two sides. One battlefield.</h2></div><span className={`provider-tag ${provider === 'local-fallback' ? 'provider-tag--fallback' : ''}`}>{provider === 'local-fallback' ? 'LOCAL FALLBACK · NOT LIVE AI' : `LIVE ANALYSIS · ${provider}`}</span></div>
            <div className="probability-row"><span>{teams[0]?.name}</span><strong>{analysis.team1_win_probability}%</strong></div>
            <div className="probability-bar"><span className="probability-bar__team1" style={{ width: `${analysis.team1_win_probability}%` }} /></div>
            <div className="probability-row"><span>{teams[1]?.name}</span><strong>{analysis.team2_win_probability}%</strong></div>
            <div className="probability-bar probability-bar--second"><span className="probability-bar__team2" style={{ width: `${analysis.team2_win_probability}%` }} /></div>
          </section>
          <section className="results-rosters">
            {teams.map((team, index) => (
              <article key={team.id} className={`results-team-card results-team-card--${index + 1}`}>
                <div className="results-team-card__head"><div><span className="eyebrow">TEAM 0{team.slot}</span><h3>{team.name}</h3></div><div className="results-team-score"><strong>${team.spent}</strong><small>of $30 spent</small></div></div>
                <div className="results-roster-grid">{team.roster.map((character) => <div className="results-character" key={character.id}><CharacterArt character={character} size="small" compact /><span>{character.display_name}</span><small>{character.identity}</small><b>${character.purchase_price}</b></div>)}</div>
              </article>
            ))}
          </section>
          <section className="analysis-grid">
            <article className="analysis-card"><span className="analysis-card__icon">⚔</span><span className="eyebrow">OVERALL COMPARISON</span><p>{analysis.overall_comparison}</p></article>
            <article className="analysis-card"><span className="analysis-card__icon">⬡</span><span className="eyebrow">OFFENSE & DEFENSE</span><p>{analysis.offense_defense_comparison}</p></article>
            <article className="analysis-card"><span className="analysis-card__icon">✦</span><span className="eyebrow">BEST TEAM COMBINATION</span><p>{analysis.best_synergy}</p></article>
            <article className="analysis-card"><span className="analysis-card__icon">◈</span><span className="eyebrow">KEY MATCHUPS</span><ul>{(analysis.key_matchups || []).map((item, i) => <li key={i}>{item}</li>)}</ul></article>
            <article className="analysis-card"><span className="analysis-card__icon">♜</span><span className="eyebrow">STRONGEST MEMBERS</span><p><b>{teams[0]?.name}:</b> {analysis.strongest_member_team1}</p><p><b>{teams[1]?.name}:</b> {analysis.strongest_member_team2}</p></article>
            <article className="analysis-card"><span className="analysis-card__icon">⚠</span><span className="eyebrow">WEAKNESSES & COUNTERS</span><p><b>{teams[0]?.name}:</b> {analysis.biggest_weakness_team1}</p><p><b>{teams[1]?.name}:</b> {analysis.biggest_weakness_team2}</p></article>
          </section>
          <section className="assumptions"><span className="eyebrow">SCENARIO ASSUMPTIONS</span><p>Universe: {match.battle_universe === 'mcu' ? 'MCU only' : 'Mixed Marvel movie continuities'} · Equipment: {match.equipment_mode === 'peak' ? 'Peak demonstrated equipment' : 'Standard equipment'} · Neutral battlefield · No external assistance.</p>{(analysis.assumptions || []).map((a, i) => <p key={i} className="assumption-item">— {a}</p>)}<small>Win percentages are estimates, not objectively proven outcomes. Live AI analysis uses provided catalog metadata and may still make mistakes.</small></section>
        </>
      )}
      <div className="results-actions"><button className="button button--gold" onClick={onPlayAgain}>↻ PLAY AGAIN</button><button className="button button--ghost" onClick={onHistory}>VIEW MATCH HISTORY</button></div>
    </main>
  );
}
