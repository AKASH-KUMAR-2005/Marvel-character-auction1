import React from 'react';
import CharacterArt from './CharacterArt';

export default function TeamPanel({ team, active = false, disabled = false, auction, onBid, onSkip, busy }) {
  if (!team) return null;
  const skipped = auction?.skipped_team_ids?.includes(team.id);
  const isLeader = auction?.leading_team_id === team.id;
  const nextBid = auction?.leading_team_id ? auction.current_bid + 1 : auction?.starting_bid;
  const canBid = auction?.status === 'active' && !disabled && !busy && !skipped && !isLeader && team.slots_remaining > 0 && team.remaining_budget >= nextBid;
  const canSkip = auction?.status === 'active' && !disabled && !busy && !skipped && !isLeader && team.skip_tokens > 0;
  return (
    <section className={`team-panel ${active ? 'team-panel--active' : ''} team-panel--${team.slot}`}>
      <div className="team-panel__topline">
        <span className="team-panel__eyebrow"><span className="team-dot" /> TEAM {String(team.slot).padStart(2, '0')}</span>
        {isLeader && <span className="leading-badge">LEADING</span>}
      </div>
      <h2>{team.name}</h2>
      <div className="team-money-row">
        <div><span className="muted-label">REMAINING</span><strong className="money-value">${team.remaining_budget}</strong></div>
        <div><span className="muted-label">SPENT</span><strong>${team.spent}</strong></div>
      </div>
      <div className="budget-track"><span style={{ width: `${Math.max(0, Math.min(100, team.remaining_budget / team.starting_budget * 100))}%` }} /></div>
      <div className="team-statline">
        <span><b>{team.character_count}</b> / 6 roster</span>
        <span><b>{team.slots_remaining}</b> slots left</span>
        <span><b>{team.skip_tokens}</b> skips</span>
      </div>
      <div className="roster-list">
        {team.roster.length ? team.roster.map((character) => (
          <div className="roster-item" key={character.id}>
            <CharacterArt character={character} size="small" compact />
            <div className="roster-item__identity"><strong>{character.display_name}</strong><span>{character.identity}</span><small>{character.universe}</small></div>
            <span className="roster-price">${character.purchase_price}</span>
          </div>
        )) : <div className="empty-roster"><span className="empty-plus">＋</span><span>Roster empty</span><small>Make your first move.</small></div>}
      </div>
      {auction?.status === 'active' && (
        <div className="team-actions">
          <button className={`bid-button ${active ? 'bid-button--primary' : ''}`} disabled={!canBid} onClick={() => onBid(team.id)}>
            <span>{isLeader ? 'YOU LEAD' : auction.leading_team_id ? 'RAISE BID' : 'OPEN BID'}</span>
            <strong>{isLeader ? 'Waiting…' : `+$${nextBid}`}</strong>
          </button>
          <button className="skip-button" disabled={!canSkip} onClick={() => onSkip(team.id)}>{skipped ? 'PASSED' : `SKIP · ${team.skip_tokens} LEFT`}</button>
        </div>
      )}
      {auction?.status === 'active' && skipped && <p className="team-note">This team passed on this character.</p>}
      {team.slots_remaining === 0 && <p className="team-note">Roster complete. No further bids allowed.</p>}
    </section>
  );
}
