// models/User.js
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true,  // This already creates an index
  },
  email: {
    type: String,
    required: true,
    unique: true,  // This already creates an index
    lowercase: true,  // Normalize to lowercase
  },
  password: {
    type: String,
    required: true,
  },
});

// Remove these duplicate index declarations
// userSchema.index({ username: 1 }, { unique: true });
// userSchema.index({ email: 1 }, { unique: true });

userSchema.pre('save', async function(){
    console.log('pre-defined', this);
});

module.exports = mongoose.model('User', userSchema);