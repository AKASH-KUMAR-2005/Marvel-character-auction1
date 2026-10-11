import React, { useState } from 'react';

export default function CharacterArt({ character, size = 'large', compact = false }) {
  const [failed, setFailed] = useState(false);
  React.useEffect(() => setFailed(false), [character?.image_url, character?.id]);
  const letters = (character?.display_name || 'MARVEL').split(/\s+/).slice(0, 2).map((word) => word[0]).join('').toUpperCase();
  return (
    <div className={`character-art character-art--${size} ${compact ? 'character-art--compact' : ''}`}>
      {character?.image_url && !failed ? (
        <img src={character.image_url} alt={`${character.display_name} — ${character.identity}`} loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <div className="character-art__placeholder" aria-label="Portrait unavailable">
          <div className="placeholder-orbit" />
          <span className="placeholder-mark">{letters || 'M'}</span>
          <span className="placeholder-label">PORTRAIT UNAVAILABLE</span>
        </div>
      )}
      {!compact && character?.image_source && !failed && <a className="image-credit" href={character.image_source} target="_blank" rel="noreferrer">Image source ↗</a>}
    </div>
  );
}
