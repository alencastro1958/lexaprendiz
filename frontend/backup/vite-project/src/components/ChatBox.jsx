import React, { useState } from 'react';
import axios from 'axios';

export default function ChatBox() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');

  const handleSend = async () => {
    try {
      const res = await axios.post('http://localhost:3000/api/chat', { question });
      setAnswer(res.data.answer);
    } catch (error) {
      setAnswer('Erro ao consultar LexAprendiz. Verifique o backend.');
    }
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial' }}>
      <h2>LexAprendiz</h2>
      <textarea
        rows="4"
        cols="60"
        placeholder="Digite sua dúvida..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <br />
      <button onClick={handleSend} style={{ marginTop: '1rem' }}>Consultar</button>
      <div style={{ marginTop: '2rem' }}>
        <strong>Resposta:</strong>
        <p>{answer}</p>
      </div>
    </div>
  );
}