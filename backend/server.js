const express = require('express');
const cors = require('cors');
const chatRoute = require('./routes/chat');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

app.use('/api/chat', chatRoute);

app.listen(3000, () => {
  console.log('LexAprendiz backend rodando na porta 3000');
});