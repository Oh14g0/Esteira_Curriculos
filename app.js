require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cors = require('cors');

const app = express();

// Middlewares
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors());

// Models
const User = require('./models/User');
const Empresa = require('./models/Empresa');

// Middleware JWT
function checkToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) return res.status(401).json({ msg: 'Acesso negado!' });

  try {
    const secret = process.env.SECRET;
    const decoded = jwt.verify(token, secret);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(400).json({ msg: 'Token inválido!' });
  }
}

// ---------------- ROTAS PÚBLICAS ----------------
app.get('/', (req, res) => {
  res.status(200).json({ msg: 'Bem-vindo à nossa API' });
});

// ---------------- ROTAS USUÁRIO ----------------

// Buscar usuário por ID
app.get('/user/:id', checkToken, async (req, res) => {
  const id = req.params.id;

  if (req.user.id !== id) return res.status(403).json({ msg: 'Acesso não autorizado' });

  try {
    const user = await User.findById(id).select('-senha');
    if (!user) return res.status(404).json({ msg: 'Usuário não encontrado' });

    res.status(200).json({ user });
  } catch (error) {
    res.status(500).json({ msg: 'Erro ao buscar usuário' });
  }
});

// Atualizar perfil do usuário
app.put('/user/:id', checkToken, async (req, res) => {
  const id = req.params.id;

  if (req.user.id !== id) return res.status(403).json({ msg: 'Acesso não autorizado' });

  const { telefone, linkedin, pretensaoSalarial, experiencias, competencias } = req.body;

  try {
    const updatedUser = await User.findByIdAndUpdate(
      id,
      { telefone, linkedin, pretensaoSalarial, experiencias, competencias },
      { new: true, runValidators: true }
    ).select('-senha');

    if (!updatedUser) return res.status(404).json({ msg: 'Usuário não encontrado para atualização' });

    res.status(200).json({ msg: 'Perfil atualizado com sucesso!', user: updatedUser });
  } catch (error) {
    res.status(500).json({ msg: 'Erro ao atualizar perfil', error: error.message });
  }
});

// Registro de usuário
app.post('/auth/register', async (req, res) => {
  const {
    nome,
    email,
    telefone,
    linkedin,
    pretensaoSalarial,
    experiencias,
    competencias,
    senha,
    confirmar_senha
  } = req.body;

  if (!nome || !email || !telefone || !linkedin || pretensaoSalarial == null || !senha || !confirmar_senha)
    return res.status(422).json({ msg: 'Todos os campos obrigatórios devem ser preenchidos!' });

  if (senha !== confirmar_senha) return res.status(422).json({ msg: 'As senhas não coincidem!' });

  const userExists = await User.findOne({ email });
  if (userExists) return res.status(422).json({ msg: 'Este email já está cadastrado!' });

  const salt = await bcrypt.genSalt(12);
  const passwordHash = await bcrypt.hash(senha, salt);

  const user = new User({
    nome,
    email,
    telefone,
    linkedin,
    pretensaoSalarial,
    experiencias,
    competencias,
    senha: passwordHash,
  });

  try {
    await user.save();
    res.status(201).json({ msg: 'Usuário criado com sucesso!' });
  } catch (error) {
    res.status(500).json({ msg: 'Erro no servidor, tente novamente mais tarde' });
  }
});

// Login do usuário
app.post('/auth/login', async (req, res) => {
  const { email, senha } = req.body;

  if (!email || !senha) return res.status(422).json({ msg: 'Email e senha são obrigatórios!' });

  const user = await User.findOne({ email });
  if (!user) return res.status(404).json({ msg: 'Usuário não encontrado!' });

  const checkPassword = await bcrypt.compare(senha, user.senha);
  if (!checkPassword) return res.status(422).json({ msg: 'Senha inválida!' });

  try {
    const secret = process.env.SECRET;
    const token = jwt.sign({ id: user._id, nome: user.nome }, secret, { expiresIn: '1h' });

    const { nome, telefone, linkedin, pretensaoSalarial, experiencias, competencias } = user;

    res.status(200).json({
      msg: 'Autenticação realizada com sucesso!',
      token,
      user: { nome, email, telefone, linkedin, pretensaoSalarial, experiencias, competencias }
    });
  } catch (error) {
    res.status(500).json({ msg: 'Erro no servidor, tente novamente mais tarde' });
  }
});

// ---------------- ROTAS EMPRESA ----------------

// Registro de empresa
app.post('/empresa/register', async (req, res) => {
  const { cnpj, nome, email, senha } = req.body;

  if (!cnpj || !nome || !email || !senha)
    return res.status(422).json({ msg: 'Todos os campos são obrigatórios!' });

  const cnpjExists = await Empresa.findOne({ cnpj });
  if (cnpjExists) return res.status(422).json({ msg: 'Este CNPJ já está cadastrado!' });

  const emailExists = await Empresa.findOne({ email });
  if (emailExists) return res.status(422).json({ msg: 'Este email já está cadastrado!' });

  const salt = await bcrypt.genSalt(12);
  const passwordHash = await bcrypt.hash(senha, salt);

  const empresa = new Empresa({
    cnpj,
    nome,
    email,
    senha: passwordHash,
  });

  try {
    await empresa.save();
    res.status(201).json({ msg: 'Empresa cadastrada com sucesso!' });
  } catch (error) {
    res.status(500).json({ msg: 'Erro interno no servidor.' });
  }
});

// Login de empresa
app.post('/auth/login-empresa', async (req, res) => {
  const { cnpj, senha } = req.body;

  if (!cnpj || !senha) return res.status(422).json({ msg: 'CNPJ e senha são obrigatórios!' });

  const empresa = await Empresa.findOne({ cnpj });
  if (!empresa) return res.status(404).json({ msg: 'Empresa não encontrada!' });

  const checkPassword = await bcrypt.compare(senha, empresa.senha);
  if (!checkPassword) return res.status(422).json({ msg: 'Senha inválida!' });

  try {
    const secret = process.env.SECRET;
    const token = jwt.sign({ id: empresa._id, nome: empresa.nome }, secret, { expiresIn: '1h' });

    res.status(200).json({
      msg: 'Autenticação realizada com sucesso!',
      token,
      empresa: {
        nome: empresa.nome,
        email: empresa.email,
        cnpj: empresa.cnpj,
      }
    });
  } catch (error) {
    res.status(500).json({ msg: 'Erro no servidor, tente novamente mais tarde' });
  }
});

// ---------------- CONEXÃO MONGODB ----------------
const dbUser = process.env.DB_USER;
const dbPassword = process.env.DB_PASS;

mongoose.connect(
  `mongodb+srv://${dbUser}:${dbPassword}@oh14g0.khedpdf.mongodb.net/?retryWrites=true&w=majority&appName=oh14g0`
)
  .then(() => {
    console.log('Conectado ao banco de dados!');
    app.listen(3000, () => console.log('Servidor rodando na porta 3000'));
  })
  .catch((err) => console.log('Erro ao conectar ao MongoDB:', err));
