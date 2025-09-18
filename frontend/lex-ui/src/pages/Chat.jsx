import React, { useState } from 'react';
import axios from 'axios';

export default function Chat() {
  const [mensagem, setMensagem] = useState('');
  const [resposta, setResposta] = useState('');
  const [carregando, setCarregando] = useState(false);

  const enviarMensagem = async () => {
    setCarregando(true);
    try {
      const res = await axios.post('http://localhost:3001/chat', { mensagem });
      setResposta(res.data.resposta);
    } catch (err) {
      setResposta('Erro ao consultar backend');
    }
    setCarregando(false);
  };

  return (
    <div style={{ maxWidth: 400, margin: '40px auto', padding: 20, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>Chat com OpenAI</h2>
      <input
        type="text"
        value={mensagem}
        onChange={e => setMensagem(e.target.value)}
        placeholder="Digite sua mensagem..."
        style={{ width: '100%', marginBottom: 10 }}
      />
      <button onClick={enviarMensagem} disabled={carregando || !mensagem} style={{ width: '100%' }}>
        {carregando ? 'Enviando...' : 'Enviar'}
      </button>
      {resposta && (
        <div style={{ marginTop: 20 }}>
          <strong>Resposta:</strong>
          <div>{resposta}</div>
        </div>
      )}
    </div>
  );
}
