// Servidor Express básico
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Importa e usa a rota de chat
const chatRouter = require('./routes/chat');
app.use('/chat', chatRouter);

app.get('/', (req, res) => {
  res.send('Backend rodando!');
});

app.listen(PORT, () => {
  console.log(`Servidor rodando na porta ${PORT}`);
});
