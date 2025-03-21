const mongoose = require('mongoose');

const connectDb = async () => {
  try {
    if (!process.env.MONGODB_URI) {
      throw new Error('MONGODB_URI environment variable is not defined');
    }
    
    await mongoose.connect(process.env.MONGODB_URI);
    console.log('Database connection established');
    return true;
  } catch (error) {
    console.error('Database connection error details:', error.message);
    console.log("Database connection error");
    return false;
  }
};

module.exports = connectDb;