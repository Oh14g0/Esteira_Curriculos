const mongoose = require('mongoose');

const empresaSchema = new mongoose.Schema({
  cnpj: { type: String, required: true, unique: true },
  nome: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  senha: { type: String, required: true },
  telefone: String,
});

module.exports = mongoose.model('Empresa', empresaSchema);
