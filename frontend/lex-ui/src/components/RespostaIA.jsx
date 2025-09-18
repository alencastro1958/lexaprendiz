import { useState, useRef } from "react";

export default function RespostaIA() {
  const [pergunta, setPergunta] = useState("");
  const [resposta, setResposta] = useState("");
  const [digitando, setDigitando] = useState(false);
  const [historico, setHistorico] = useState(() => {
    const salvo = localStorage.getItem("historico");
    return salvo ? JSON.parse(salvo) : [];
  });

  const respostaRef = useRef(null);
  const synth = window.speechSynthesis;

  const consultarIA = async () => {
    if (!pergunta.trim()) return;

    setResposta("");
    setDigitando(true);

    try {
      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${import.meta.env.VITE_OPENAI_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4",
          messages: [{ role: "user", content: pergunta }],
          stream: true,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        buffer += chunk;

        const lines = buffer.split("\n").filter(line => line.trim() !== "");

        for (let line of lines) {
          if (line.startsWith("data: ")) {
            const json = line.replace("data: ", "");
            if (json === "[DONE]") break;

            try {
              const parsed = JSON.parse(json);
              const delta = parsed.choices?.[0]?.delta?.content;
              if (delta) {
                setResposta(prev => prev + delta);
              }
            } catch (err) {
              console.error("Erro ao processar chunk:", err);
            }
          }
        }
      }

      setDigitando(false);

      const novoHistorico = [{ pergunta, resposta: buffer }, ...historico];
      setHistorico(novoHistorico);
      localStorage.setItem("historico", JSON.stringify(novoHistorico));
    } catch (error) {
      console.error("Erro na consulta à API:", error);
      setDigitando(false);
      setResposta("❌ Ocorreu um erro ao consultar a IA.");
    }
  };

  const falarResposta = () => {
    if (synth.speaking) synth.cancel();
    const utter = new SpeechSynthesisUtterance(resposta);
    utter.lang = "pt-BR";
    synth.speak(utter);
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "1rem" }}>
      <h2>LexAprendiz</h2>
      <input
        type="text"
        value={pergunta}
        onChange={(e) => setPergunta(e.target.value)}
        placeholder="Digite sua pergunta"
        style={{ width: "100%", padding: "0.5rem", marginBottom: "0.5rem" }}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button onClick={consultarIA}>Consultar</button>
        <button onClick={falarResposta}>🔊 Ouvir</button>
      </div>

      <div
        ref={respostaRef}
        style={{
          marginTop: "1rem",
          background: "#f9f9f9",
          padding: "1rem",
          borderRadius: "8px",
          whiteSpace: "pre-wrap",
          minHeight: "100px",
        }}
      >
        {digitando ? "⏳ Respondendo..." : resposta}
      </div>

      <h3 style={{ marginTop: "2rem" }}>Histórico de Consultas</h3>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {historico.map((item, i) => (
          <li key={i} style={{ marginBottom: "1rem", borderBottom: "1px solid #ccc", paddingBottom: "0.5rem" }}>
            <strong>{item.pergunta}</strong>
            <p>{item.resposta}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
