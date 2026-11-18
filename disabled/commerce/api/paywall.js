/**
 * Paywall Service - Klein Digital Solutions
 * Credit verification and service access control
 * Vercel Serverless Function
 */

module.exports = async function handler(req, res) {
    // Set CORS headers for both domains
    const allowedOrigins = [
        'https://studio.kleindigitalsolutions.de',
        'http://localhost:3000'
    ];
    
    const origin = req.headers.origin;
    
    if (allowedOrigins.includes(origin)) {
        res.setHeader('Access-Control-Allow-Origin', origin);
    } else {
        res.setHeader('Access-Control-Allow-Origin', '*');
    }
    
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    
    // Handle preflight request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    // Only allow POST requests
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    try {
        const { 
            userId, 
            userEmail, 
            service,
            requiredCredits = 1 
        } = req.body;
        
        if (!userId && !userEmail) {
            return res.status(400).json({ 
                error: 'User identification required',
                requiresAuth: true 
            });
        }
        
        if (!service) {
            return res.status(400).json({ error: 'Service type required' });
        }

        // Check user credit balance
        const creditCheck = await checkUserCredits(userId, userEmail, requiredCredits);
        
        if (!creditCheck.hasEnoughCredits) {
            return res.status(402).json({
                error: 'Insufficient credits',
                paymentRequired: true,
                currentBalance: creditCheck.currentBalance,
                required: requiredCredits,
                shortfall: creditCheck.shortfall,
                recommendedPackage: getRecommendedPackage(creditCheck.shortfall),
                service: service
            });
        }

        // User has enough credits - return access token
        const accessToken = generateAccessToken(userId || userEmail, service);
        
        return res.status(200).json({
            access: 'granted',
            accessToken: accessToken,
            currentBalance: creditCheck.currentBalance,
            service: service,
            willDeduct: requiredCredits,
            balanceAfter: creditCheck.currentBalance - requiredCredits
        });
        
    } catch (error) {
        console.error('Paywall error:', error);
        return res.status(500).json({ 
            error: 'Paywall service error',
            message: error.message 
        });
    }
}

async function checkUserCredits(userId, userEmail, requiredCredits) {
    try {
        // Call the credits API to get user balance
        const userKey = userId || `email_${userEmail}`;
        const user = await getUser(userKey, userEmail);
        
        const hasEnoughCredits = user.credits >= requiredCredits;
        const shortfall = hasEnoughCredits ? 0 : requiredCredits - user.credits;
        
        return {
            hasEnoughCredits,
            currentBalance: user.credits,
            shortfall,
            user
        };
        
    } catch (error) {
        console.error('Credit check error:', error);
        return {
            hasEnoughCredits: false,
            currentBalance: 0,
            shortfall: requiredCredits,
            user: null
        };
    }
}

function getRecommendedPackage(shortfall) {
    // Recommend package based on shortfall
    if (shortfall <= 1) {
        return {
            id: 'single',
            name: '1 Credit Pack - Launch Special',
            price: '€3.49',
            credits: 1,
            priceId: 'price_SINGLE_CREDIT_ID' // TODO: Add actual price ID
        };
    } else if (shortfall <= 10) {
        return {
            id: 'starter',
            name: '10 Credits Pack - Launch Special',
            price: '€24.99',
            credits: 10,
            priceId: 'price_1RnxJsAmspxoSxsTWG1nkwdL'
        };
    } else if (shortfall <= 25) {
        return {
            id: 'pro',
            name: '25 Credits Pack - Launch Special',
            price: '€49.99',
            credits: 25,
            priceId: 'price_1RnxMNAmspxoSxsT13PcPtQW'
        };
    } else {
        return {
            id: 'studio',
            name: '50 Credits Pack - Launch Special',
            price: '€79.99',
            credits: 50,
            priceId: 'price_1RnxO0AmspxoSxsTVTuTSQSe'
        };
    }
}

function generateAccessToken(userIdentifier, service) {
    // Simple access token generation
    const timestamp = Date.now();
    const payload = {
        user: userIdentifier,
        service: service,
        timestamp: timestamp,
        expires: timestamp + (10 * 60 * 1000) // 10 minutes
    };
    
    // In production, use proper JWT or encryption
    return Buffer.from(JSON.stringify(payload)).toString('base64');
}

// Simplified user retrieval (matches credits.js logic)
async function getUser(userId, userEmail) {
    const userKey = userId || `email_${userEmail}`;
    
    // In production, this would query your database
    // For now, return default user structure
    if (typeof localStorage !== 'undefined') {
        const userData = localStorage.getItem(`user_${userKey}`);
        if (userData) {
            return JSON.parse(userData);
        }
    }
    
    // Default user with 0 credits
    return {
        id: userId || generateId(),
        email: userEmail || '',
        credits: 0,
        createdAt: new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
        packages: [],
        usage: []
    };
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}