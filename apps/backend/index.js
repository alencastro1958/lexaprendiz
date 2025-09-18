const express = require('express');
const cors = require('cors');
const OpenAI = require('openai');
const { PrismaClient } = require('@prisma/client');
require('dotenv').config();

const app = express();
const prisma = new PrismaClient();

// Garante que a tabela exista mesmo se o Prisma "db push" falhar (ambiente dev / Windows lock)
(async () => {
  try {
    await prisma.$executeRawUnsafe(`CREATE TABLE IF NOT EXISTS "Consulta" (
      "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
      "perguntaA" TEXT NOT NULL,
      "respostaA" TEXT NOT NULL,
      "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )`);
    // Opcional: criar índice simples para buscas futuras (ignora erro se já existir)
    try { await prisma.$executeRaw`CREATE INDEX IF NOT EXISTS idx_consulta_perguntaA ON "Consulta" ("perguntaA")`; } catch(_) {}
  } catch (e) {
    console.error('Falha ao garantir tabela Consulta:', e.message);
  }
})();

const allowedOrigins = [
  'http://localhost:5173',
  'http://localhost:3000',
  'https://leidaaprendizagembr.com.br'
];

app.use(cors({
  origin: (origin, cb) => {
    if (!origin || allowedOrigins.includes(origin)) {
      return cb(null, true);
    }
    return cb(new Error('Origem não permitida: ' + origin));
  },
  methods: ['GET','POST','OPTIONS'],
  allowedHeaders: ['Content-Type','Authorization']
}));
app.use(express.json());

if (!process.env.OPENAI_API_KEY) {
  console.warn('⚠️  OPENAI_API_KEY não definida. Modo teste.');
}
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

app.post('/api/chat', async (req, res) => {
  const question = req.body.question || req.body.mensagem;
  if (!question) {
    return res.status(400).json({ error: 'Campo question ou mensagem é obrigatório.' });
  }
  try {
    let answer;
    if (!process.env.OPENAI_API_KEY) {
      answer = '(modo teste) Defina OPENAI_API_KEY para respostas reais.';
    } else {
      const completion = await openai.chat.completions.create({
        model: 'gpt-3.5-turbo',
        messages: [
          { role: 'system', content: 'Você é LexAprendiz, um assistente jurídico pedagógico.' },
          { role: 'user', content: question }
        ]
      });
      answer = completion.choices[0].message.content;
    }
    await prisma.consulta.create({ data: { perguntaA: question, respostaA: answer } });
    res.json({ answer });
  } catch (error) {
    const status = error.status || error.response?.status;
    // Log minimizado para não vazar dados sensíveis
    console.error('Erro /api/chat:', { message: error.message, status });
    if (status === 429) {
      const fallback = 'Limite de uso / quota da API de IA excedido. Tente novamente mais tarde.';
      try { await prisma.consulta.create({ data: { perguntaA: question, respostaA: fallback } }); } catch (_) {}
      return res.status(429).json({ error: 'Quota excedida', message: fallback });
    }
    const generic = 'Falha ao gerar resposta.';
    try { await prisma.consulta.create({ data: { perguntaA: question, respostaA: generic } }); } catch (_) {}
    res.status(500).json({ error: generic });
  }
});

app.get('/api/historico', async (req, res) => {
  const { busca } = req.query;
  try {
    const consultas = await prisma.consulta.findMany({
      where: busca ? {
        OR: [
          { perguntaA: { contains: busca, mode: 'insensitive' } },
          { respostaA: { contains: busca, mode: 'insensitive' } }
        ]
      } : {},
  orderBy: { createdAt: 'desc' }
    });
    res.json(consultas);
  } catch (error) {
    console.error('Erro /api/historico:', error.message);
    res.status(500).json({ error: 'Falha ao buscar histórico.' });
  }
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log('Backend LexAprendiz em http://localhost:' + PORT));
