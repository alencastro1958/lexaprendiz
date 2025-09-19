import { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function Home() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [aiHealth, setAiHealth] = useState(null); // { ok, status, reason, message }

  const handleSubmit = async () => {
    if (!question.trim()) {
      return;
    }
    setLoading(true); setError(''); setAnswer('');
    try {
      const res = await api.post('/api/chat', { question });
      setAnswer(res.data.answer);
      fetchHistorico();
    } catch (e) {
      setError('Falha ao consultar IA: ' + (e.response?.data?.error || e.message));
    } finally { setLoading(false); }
  };

  const fetchHistorico = async () => {
    try {
      const res = await api.get('/api/historico');
      setHistorico(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAiHealth = async () => {
    try {
      const res = await api.get('/health/ai');
      setAiHealth(res.data);
    } catch (e) {
      // Em caso de falha de rede/servidor, marcar como desconhecido
      setAiHealth({ ok: false, status: e.response?.status || 0, reason: 'unreachable', message: e.message });
    }
  };

  useEffect(() => { fetchHistorico(); fetchAiHealth(); }, []);

  const renderAiBanner = () => {
    if (!aiHealth) return null;
    const baseStyle = { padding: '0.5rem 0.75rem', borderRadius: 6, marginBottom: '1rem', display: 'inline-block' };
    let style = { ...baseStyle, background: '#eef2ff', color: '#1e40af', border: '1px solid #c7d2fe' };
    let text = 'IA: pronto';
    if (aiHealth.status === 'no-key') {
      style = { ...baseStyle, background: '#fef9c3', color: '#854d0e', border: '1px solid #fde68a' };
      text = 'IA em modo teste (sem OPENAI_API_KEY)';
    } else if (aiHealth.status === 401) {
      style = { ...baseStyle, background: '#fee2e2', color: '#7f1d1d', border: '1px solid #fecaca' };
      text = 'IA indisponível: chave inválida (401)';
    } else if (aiHealth.status === 429 || aiHealth.reason === 'quota-exceeded') {
      style = { ...baseStyle, background: '#ffedd5', color: '#7c2d12', border: '1px solid #fed7aa' };
      text = 'IA indisponível: quota excedida (429)';
    } else if (aiHealth.ok === true) {
      style = { ...baseStyle, background: '#dcfce7', color: '#14532d', border: '1px solid #bbf7d0' };
      text = 'IA disponível';
    } else if (aiHealth.reason === 'unreachable') {
      style = { ...baseStyle, background: '#fee2e2', color: '#7f1d1d', border: '1px solid #fecaca' };
      text = 'IA: serviço indisponível (backend)';
    }
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <span style={style}>{text}</span>
        <button onClick={fetchAiHealth} style={{ padding: '0.3rem 0.5rem' }}>Rechecar</button>
      </div>
    );
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial' }}>
      <h1>LexAprendiz</h1>
  {renderAiBanner()}
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Digite sua pergunta"
        style={{ width: '100%', padding: '0.5rem', marginBottom: '1rem' }}
      />
      <button onClick={handleSubmit} disabled={loading}>{loading ? 'Consultando...' : 'Consultar'}</button>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {answer && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Resposta</h2>
          <p>{answer}</p>
        </div>
      )}

      <div style={{ marginTop: '3rem' }}>
        <h2>Histórico de Consultas</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {historico.map(item => (
            <li key={item.id} style={{ marginBottom: '1rem', borderBottom: '1px solid #ccc' }}>
              <strong>Pergunta:</strong> {item.perguntaA}<br />
              <strong>Resposta:</strong> {item.respostaA}<br />
              <em>{new Date(item.createdAt || item.criaçãoEm).toLocaleString()}</em>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
