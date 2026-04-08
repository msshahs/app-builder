require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const authRoutes = require('./routes/auth');
const errorHandler = require('./middleware/errorHandler');

const app = express();

// Security middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Rate limiting on auth routes
const authLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100
});
app.use('/auth', authLimiter);

// Fixed auth routes — always at /auth
app.use('/auth', authRoutes);

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok' }));

// Dynamic routes injected by agents — imported from routes/index.js
try {
    const appRoutes = require('./routes/index');
    app.use('/api', appRoutes);
} catch (e) {
    console.log('No app routes found — auth only mode');
}

// Error handler
app.use(errorHandler);

// Connect to MongoDB and start server
mongoose.connect(process.env.MONGO_URI)
    .then(() => {
        console.log('MongoDB connected');
        const PORT = process.env.PORT || 5000;
        app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
    })
    .catch(err => {
        console.error('MongoDB connection error:', err);
        process.exit(1);
    });