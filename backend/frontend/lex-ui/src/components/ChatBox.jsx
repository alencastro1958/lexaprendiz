import React, { useState } from 'react';
import axios from 'axios';

export default function ChatBox() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSend = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError('');
    setAnswer('');

    try {
      const res = await axios.post('http://localhost:3000/api/chat', { question });
      setAnswer(res.data.answer);
    } catch (err) {
      console.error('API error:', err);
      setError(`Erro ao consultar LexAprendiz: ${err.message || 'Verifique o backend ou a conexão.'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial' }}>
      <h2>LexAprendiz</h2>
      <textarea
        rows="4"
        cols="60"
        placeholder="Digite sua dúvida jurídica ou pedagógica..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <br />
      <button onClick={handleSend} disabled={loading} style={{ marginTop: '1rem' }}>
        {loading ? 'Consultando...' : 'Consultar'}
      </button>

      {error && (
        <div style={{ marginTop: '1rem', color: 'red' }}>
          <strong>{error}</strong>
        </div>
      )}

      {answer && (
        <div style={{ marginTop: '2rem' }}>
          <strong>Resposta:</strong>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}