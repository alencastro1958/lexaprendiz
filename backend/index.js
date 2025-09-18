<<<<<<< HEAD
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

    // ✅ Salvar no banco com campos ajustados
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

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`LexAprendiz backend rodando com IA em http://localhost:${PORT}`);
});
=======
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const chatRouter = require('./routes/chat');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use('/chat', chatRouter);

app.get('/', (req, res) => {
  res.send('Backend rodando!');
});

app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});
>>>>>>> 3f40959 (Backend LexAprendiz)
