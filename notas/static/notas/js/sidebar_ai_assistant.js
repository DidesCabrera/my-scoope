document.addEventListener("DOMContentLoaded", () => {
    const button = document.querySelector(".js-copy-chatgpt-prompt");
    const promptTemplate = document.getElementById("sidebar-ai-prompt");
    const feedback = document.querySelector(".js-copy-chatgpt-feedback");
  
    if (!button) return;
  
    const fallbackPrompt = `
  Actúa como asistente experto de My Scoope.
  
  Ayúdame a usar la plataforma para construir, analizar y mejorar mis minutas diarias de alimentación, comidas y alimentos.
  
  Contexto de My Scoope:
  - My Scoope permite gestionar minutas diarias de alimentación.
  - Una minuta diaria contiene comidas.
  - Una comida contiene alimentos y porciones.
  - Los KPIs principales son kcal totales, proteína, carbohidratos, grasas, PPK y distribución calórica.
  - En esta conversación no tienes acceso directo a mi cuenta ni a mis datos de My Scoope, salvo que yo te los entregue.
  - No inventes datos: si necesitas información del plan, comida o alimento, pídemela.
  
  Primero pregúntame qué quiero lograr hoy dentro de My Scoope.
  Luego guíame paso a paso con instrucciones claras.
  `.trim();
  
    function setFeedback(message) {
      if (!feedback) return;
      feedback.textContent = message;
    }
  
    function getPrompt() {
      const templateContentPrompt = promptTemplate?.content?.textContent?.trim();
      if (templateContentPrompt) return templateContentPrompt;
  
      const templateTextPrompt = promptTemplate?.textContent?.trim();
      if (templateTextPrompt) return templateTextPrompt;
  
      const dataPrompt = button.dataset.prompt?.trim();
      if (dataPrompt) return dataPrompt;
  
      return fallbackPrompt;
    }
  
    async function copyText(text) {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }
  
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.top = "-9999px";
      textarea.style.left = "-9999px";
  
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
  
    button.addEventListener("click", async () => {
      const prompt = getPrompt();
      const chatgptUrl = button.dataset.chatgptUrl || "https://chatgpt.com/";
  
      try {
        await copyText(prompt);
  
        setFeedback("Prompt copiado. Pégalo en ChatGPT.");
  
        const openedWindow = window.open(chatgptUrl, "_blank", "noopener,noreferrer");
  
        if (!openedWindow) {
          setFeedback("Prompt copiado. Abre ChatGPT y pégalo manualmente.");
        }
      } catch (error) {
        setFeedback("No se pudo copiar. Inténtalo manualmente.");
        console.error("Could not copy ChatGPT prompt:", error);
      }
    });
  });