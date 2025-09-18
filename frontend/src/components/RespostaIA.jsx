import React from 'react';

export default function RespostaIA({ resposta }) {
  return (
    <div style={{ marginTop: 20, padding: 10, border: '1px solid #ccc', borderRadius: 8 }}>
      <strong>Resposta da IA:</strong>
      <p>{resposta}</p>
    </div>
  );
}
