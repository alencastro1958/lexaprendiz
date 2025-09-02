const express = require('express');
const cors = require('cors');
const { Configuration, OpenAI } = require('openai');
const { PrismaClient } = require('@prisma/client');
require('dotenv').config();

const app = express();
const prisma = new PrismaClient();

app.use(cors());
app.use(express.json());

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 🔹 Rota para gerar resposta com IA e salvar no banco
app.post('/api/chat', async (req, res) => {
  const { question } = req.body;

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        {
          role: 'system',
          content: 'Você é LexAprendiz, um assistente jurídico-pedagógico especializado em legislação brasileira sobre aprendizagem profissional. Responda com clareza, formalidade e base legal sempre que possível.',
        },
        {
          role: 'user',
          content: question,
        },
      ],
    });

    const answer = completion.choices[0].message.content;

    await prisma.consulta.create({
      data: {
        perguntaA: question,
        respostaA: answer,
      },
    });

    res.json({ answer });
  } catch (error) {
    console.error('Erro na API OpenAI:', error.message);
    res.status(500).json({ error: 'Erro ao gerar resposta com IA.' });
  }
});

// 🔹 Rota para listar histórico com filtros opcionais
app.get('/api/historico', async (req, res) => {
  const { busca, data } = req.query;

  try {
    const consultas = await prisma.consulta.findMany({
      where: {
        AND: [
          busca
            ? {
                OR: [
                  { perguntaA: { contains: busca, mode: 'insensitive' } },
                  { respostaA: { contains: busca, mode: 'insensitive' } },
                ],
              }
            : {},
          data
            ? {
                criaçãoEm: {
                  gte: new Date(data),
                },
              }
            : {},
        ],
      },
      orderBy: {
        criaçãoEm: 'desc',
      },
    });

    res.json(consultas);
  } catch (error) {
    console.error('Erro ao buscar histórico:', error.message);
    res.status(500).json({ error: 'Erro ao buscar histórico.' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`LexAprendiz backend rodando com IA em http://localhost:${PORT}`);
});