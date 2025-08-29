const express = require('express');
const axios = require('axios');
const router = express.Router();

router.post('/', async (req, res) => {
  const { question } = req.body;

  try {
    const response = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'Você é LexAprendiz, um consultor jurídico, pedagógico e administrativo especializado em legislação brasileira sobre aprendizagem profissional. Responda com clareza, formalidade e acessibilidade, citando fontes legais quando possível.'
          },
          {
            role: 'user',
            content: question
          }
        ],
        temperature: 0.3
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.OPENAI_API_KEY}`
        }
      }
    );

    res.json({ answer: response.data.choices[0].message.content });
  } catch (error) {
    res.status(500).json({ error: 'Erro ao consultar a IA.' });
  }
});

module.exports = router;