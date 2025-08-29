import React from 'react';
import ChatBox from '../components/ChatBox';

export default function Home() {
  return (
    <div>
      <header style={{ backgroundColor: '#003366', color: '#fff', padding: '1rem' }}>
        <h1>LexAprendiz</h1>
        <p>Seu guia legal na jornada da aprendizagem profissional</p>
      </header>
      <ChatBox />
    </div>
  );
}