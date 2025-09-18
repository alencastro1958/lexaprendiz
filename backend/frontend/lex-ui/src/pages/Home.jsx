import { useState, useEffect } from 'react';
import axios from 'axios';

export default function Home() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [historico, setHistorico] = useState([]);

  const handleSubmit = async () => {
    try {
      const res = await axios.post('https://lexaprendiz-backend.onrender.com/api/chat', {
        question,
      });
      setAnswer(res.data.answer);
      fetchHistorico(); // Atualiza histórico após nova consulta
    } catch (error) {
      console.error('Erro ao consultar IA:', error);
    }
  };

  const fetchHistorico = async () => {
    try {
      const res = await axios.get('https://lexaprendiz-backend.onrender.com/api/historico');
      setHistorico(res.data);
    } catch (error) {
      console.error('Erro ao buscar histórico:', error);
    }
  };

  useEffect(() => {
    fetchHistorico();
  }, []);

  return (
    <div style={{ padding: '2rem' }}>
      <h1>LexAprendiz</h1>
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Digite sua pergunta"
        style={{ width: '100%', padding: '0.5rem', marginBottom: '1rem' }}
      />
      <button onClick={handleSubmit}>Consultar</button>

      {answer && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Resposta</h2>
          <p>{answer}</p>
        </div>
      )}

      <div style={{ marginTop: '3rem' }}>
        <h2>Histórico de Consultas</h2>
        <ul>
          {historico.map((item) => (
            <li key={item.id} style={{ marginBottom: '1rem' }}>
              <strong>Pergunta:</strong> {item.perguntaA}<br />
              <strong>Resposta:</strong> {item.respostaA}<br />
              <em>{new Date(item.criaçãoEm).toLocaleString()}</em>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}