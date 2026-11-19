"use strict";

const busca = document.querySelector("#busca");
const reserva = document.querySelector("#reserva");
const filtros = document.querySelector("#filtros");
const escolha = document.querySelector("#escolha");
const entrada = document.querySelector("#entrada");
const aplicacao = document.querySelector("#aplicacao");
const usuarioAtual = document.querySelector("#usuario-atual");
const sair = document.querySelector("#sair");
const filtro = document.querySelector("#filtro");
const dia = document.querySelector("#dia");
const horarios = document.querySelector("#horarios");
const confirmar = document.querySelector("#confirmar");
const mensagemHorarios = document.querySelector("#mensagem-horarios");
const mensagemReserva = document.querySelector("#mensagem-reserva");
let carregando = false;
let agendando = false;
let buscaPendente = null;
let sessao = null; // { token, nome, papel }: o que um login real deixaria no cliente

function lerSessao() {
    try {
        return JSON.parse(sessionStorage.getItem("sessao"));
    } catch {
        return null;
    }
}

function guardarSessao(valor) {
    try {
        if (valor) {
            sessionStorage.setItem("sessao", JSON.stringify(valor));
        } else {
            sessionStorage.removeItem("sessao");
        }
    } catch {
        // Sem armazenamento a sessão vale só até recarregar a página.
    }
}

function mostrarSessao() {
    const conectado = sessao !== null;
    entrada.hidden = conectado;
    aplicacao.hidden = !conectado;
    usuarioAtual.hidden = !conectado;
    sair.hidden = !conectado;
    usuarioAtual.textContent = conectado ? `Conectado como ${sessao.nome} (${sessao.papel})` : "";
}

const amanha = new Date();
amanha.setDate(amanha.getDate() + 1);
dia.value = [amanha.getFullYear(), amanha.getMonth() + 1, amanha.getDate()]
    .map(parte => String(parte).padStart(2, "0")).join("-");

function mensagem(elemento, texto, tipo = "") {
    elemento.textContent = texto;
    elemento.dataset.tipo = tipo;
}

function selecionado() {
    return horarios.querySelector('input[name="slot"]:checked');
}

function definirCarregamento(ativo) {
    carregando = ativo;
    sair.disabled = agendando;
    filtros.disabled = ativo;
    escolha.disabled = ativo;
    escolha.setAttribute("aria-busy", String(ativo));
    confirmar.disabled = ativo || !selecionado();
}

async function chamarApi(caminho, token, opcoes = {}) {
    let resposta;
    try {
        resposta = await fetch(caminho, {
            ...opcoes,
            headers: { ...opcoes.headers, Authorization: `Bearer ${token}` },
        });
    } catch {
        throw new Error("Não foi possível acessar a API. Verifique a conexão e tente novamente.");
    }
    const dados = await resposta.json().catch(() => null);
    if (!resposta.ok || dados === null) {
        throw new Error(dados?.erro || "A API não conseguiu concluir a solicitação.");
    }
    return dados;
}

function limparHorarios() {
    horarios.replaceChildren();
    confirmar.disabled = true;
}

function mostrarHorarios(disponibilidade) {
    limparHorarios();
    let total = 0;
    for (const { profissional, slots } of disponibilidade) {
        if (slots.length === 0) {
            continue;
        }
        const grupo = document.createElement("section");
        grupo.className = "profissional";
        const nome = document.createElement("h3");
        nome.textContent = profissional.nome;
        const especialidade = document.createElement("p");
        especialidade.textContent = profissional.especialidade;
        const opcoes = document.createElement("div");
        opcoes.className = "opcoes";

        for (const slot of slots) {
            const opcao = document.createElement("label");
            opcao.className = "opcao";
            const escolhaDoSlot = document.createElement("input");
            escolhaDoSlot.type = "radio";
            escolhaDoSlot.name = "slot";
            escolhaDoSlot.value = slot.inicio;
            escolhaDoSlot.dataset.profissionalId = profissional.id;
            escolhaDoSlot.dataset.profissionalNome = profissional.nome;
            const intervalo = `${slot.inicio.slice(11, 16)}–${slot.fim.slice(11, 16)}`;
            escolhaDoSlot.setAttribute("aria-label", `${intervalo}, ${profissional.nome}`);
            opcao.append(escolhaDoSlot, intervalo);
            opcoes.append(opcao);
        }

        grupo.append(nome, especialidade, opcoes);
        horarios.append(grupo);
        total += slots.length;
    }
    mensagem(mensagemHorarios, total ? "Selecione um horário abaixo." : "Nenhum horário disponível nessa data.");
}

async function consultarHorarios() {
    const controlador = new AbortController();
    const sessaoDaBusca = sessao;
    buscaPendente = controlador;
    definirCarregamento(true);
    limparHorarios();
    mensagem(mensagemHorarios, "Consultando disponibilidade…");
    const opcao = filtro.selectedOptions[0];
    const parametros = new URLSearchParams({ dia: dia.value, [opcao.dataset.parametro]: opcao.value });
    try {
        const disponibilidade = await chamarApi(`/disponibilidade?${parametros}`, sessaoDaBusca.token, {
            signal: controlador.signal,
        });
        if (buscaPendente === controlador && sessao === sessaoDaBusca) {
            mostrarHorarios(disponibilidade);
        }
    } catch (erro) {
        if (buscaPendente === controlador && sessao === sessaoDaBusca && !controlador.signal.aborted) {
            mensagem(mensagemHorarios, erro.message, "erro");
        }
    } finally {
        if (buscaPendente === controlador) {
            buscaPendente = null;
            definirCarregamento(false);
        }
    }
}

busca.addEventListener("change", () => {
    limparHorarios();
    mensagem(mensagemHorarios, "Consulte a disponibilidade para os filtros atuais.");
    mensagem(mensagemReserva, "");
});

busca.addEventListener("submit", async evento => {
    evento.preventDefault();
    if (carregando) {
        return;
    }
    mensagem(mensagemReserva, "");
    await consultarHorarios();
});

reserva.addEventListener("change", () => {
    confirmar.disabled = carregando || !selecionado();
    mensagem(mensagemReserva, "");
});

reserva.addEventListener("submit", async evento => {
    evento.preventDefault();
    const slot = selecionado();
    if (carregando || !slot) {
        return;
    }
    agendando = true;
    definirCarregamento(true);
    mensagem(mensagemReserva, "Registrando agendamento…");
    let consulta;
    try {
        consulta = await chamarApi("/consultas", sessao.token, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profissional_id: Number(slot.dataset.profissionalId), inicio: slot.value }),
        });
        const data = consulta.inicio.slice(0, 10).split("-").reverse().join("/");
        const hora = consulta.inicio.slice(11, 16);
        mensagem(mensagemReserva, `Agendamento registrado (#${consulta.id}) com ${slot.dataset.profissionalNome} em ${data} às ${hora}.`, "sucesso");
    } catch (erro) {
        mensagem(mensagemReserva, erro.message, "erro");
    } finally {
        agendando = false;
        definirCarregamento(false);
    }
    if (consulta) {
        await consultarHorarios();
    }
});

entrada.addEventListener("click", evento => {
    const botao = evento.target.closest("button[data-token]");
    if (!botao) {
        return;
    }
    const { token, nome, papel } = botao.dataset;
    sessao = { token, nome, papel };
    guardarSessao(sessao);
    mostrarSessao();
});

sair.addEventListener("click", () => {
    if (agendando) {
        return;
    }
    const buscaAnterior = buscaPendente;
    buscaPendente = null;
    buscaAnterior?.abort();
    definirCarregamento(false);
    sessao = null;
    guardarSessao(null);
    limparHorarios();
    mensagem(mensagemHorarios, "Consulte a disponibilidade para escolher um horário.");
    mensagem(mensagemReserva, "");
    mostrarSessao();
});

sessao = lerSessao();
mostrarSessao();
