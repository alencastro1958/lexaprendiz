const express = require('express');
const router = express.Router();


const { Configuration, OpenAIApi } = require('openai');
require('dotenv').config();

const configuration = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});
const openai = new OpenAIApi(configuration);

router.post('/', async (req, res) => {
  const { mensagem } = req.body;
  try {
    const completion = await openai.createChatCompletion({
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'user', content: mensagem }
      ]
    });
    const resposta = completion.data.choices[0].message.content;
    res.json({ resposta });
  } catch (error) {
    console.error(error);
    res.status(500).json({ erro: 'Erro ao consultar OpenAI' });
  }
});

module.exports = router;
