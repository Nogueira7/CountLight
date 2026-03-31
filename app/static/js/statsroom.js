document.addEventListener("DOMContentLoaded", async function () {

  if (!ROOM_ID) return;

  try {

    const response = await fetch(`/api/rooms/${ROOM_ID}/energy`);

    if (!response.ok) {
      console.error("Erro ao buscar dados da divisão");
      return;
    }

    const readings = await response.json();

    console.log("Leituras da divisão:", readings);

  } catch (error) {
    console.error("Erro:", error);
  }

});
