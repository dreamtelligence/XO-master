/**
 * Secure Credit Management API - Klein Digital Solutions
 * Handles credit balance, deduction, and usage tracking
 * Uses Supabase for tamper-proof storage with RLS
 */

import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client with service role (server-side only)
const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
);

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
    
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    
    // Handle preflight request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    // Validate Supabase configuration
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
        return res.status(500).json({ 
            error: 'Supabase configuration missing',
            note: 'Add NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to environment variables'
        });
    }

    try {
        switch (req.method) {
            case 'GET':
                return await handleGetCredits(req, res);
            case 'POST':
                return await handleAddCredits(req, res);
            case 'PUT':
                return await handleDeductCredits(req, res);
            default:
                return res.status(405).json({ error: 'Method not allowed' });
        }
    } catch (error) {
        console.error('Credits API error:', error);
        return res.status(500).json({ 
            error: 'Internal server error',
            message: error.message 
        });
    }
}

// GET /api/credits?userId=xxx - Get user credit balance
async function handleGetCredits(req, res) {
    const { userId, userEmail } = req.query;
    
    if (!userId && !userEmail) {
        return res.status(400).json({ error: 'userId or userEmail required' });
    }

    const user = await getOrCreateUser(userId, userEmail);
    const purchases = await getUserPurchases(user.id);
    const usage = await getUserUsage(user.id);
    
    return res.status(200).json({
        userId: user.id,
        email: user.email,
        credits: user.credits,
        lastUpdated: user.updated_at,
        packages: purchases,
        usage: usage.slice(0, 10) // Last 10 usage records
    });
}

// POST /api/credits - Add credits to user account (SECURED - Only via webhook)
async function handleAddCredits(req, res) {
    const { 
        userId, 
        userEmail, 
        credits, 
        packageType, 
        sessionId,
        paymentAmount,
        webhookSecret
    } = req.body;
    
    // Security: Only allow credit addition via webhook
    if (webhookSecret !== process.env.CREDIT_WEBHOOK_SECRET) {
        return res.status(403).json({ error: 'Unauthorized credit addition' });
    }
    
    if (!userId && !userEmail) {
        return res.status(400).json({ error: 'userId or userEmail required' });
    }
    
    if (!credits || credits <= 0) {
        return res.status(400).json({ error: 'Valid credit amount required' });
    }

    const user = await getOrCreateUser(userId, userEmail);
    
    // Add credits using database transaction
    const { data, error } = await supabase.rpc('add_user_credits', {
        p_user_id: user.id,
        p_credits: credits,
        p_package_type: packageType || 'unknown',
        p_session_id: sessionId,
        p_payment_amount: paymentAmount
    });
    
    if (error) {
        console.error('Failed to add credits:', error);
        return res.status(500).json({ error: 'Failed to add credits' });
    }
    
    console.log(`💎 Added ${credits} credits to user ${user.id}. New balance: ${data[0].new_balance}`);
    
    return res.status(200).json({
        userId: user.id,
        email: user.email,
        credits: data[0].new_balance,
        creditsAdded: credits,
        transactionId: data[0].transaction_id
    });
}

// PUT /api/credits - Deduct credits for service usage
async function handleDeductCredits(req, res) {
    const { 
        userId, 
        userEmail, 
        credits = 1, 
        service,
        jobId 
    } = req.body;
    
    if (!userId && !userEmail) {
        return res.status(400).json({ error: 'userId or userEmail required' });
    }
    
    if (!service) {
        return res.status(400).json({ error: 'service type required' });
    }

    const user = await getOrCreateUser(userId, userEmail);
    
    // Check if user has enough credits
    if (user.credits < credits) {
        return res.status(402).json({ 
            error: 'Insufficient credits',
            currentBalance: user.credits,
            required: credits,
            shortfall: credits - user.credits
        });
    }
    
    // Deduct credits using database transaction
    const { data, error } = await supabase.rpc('deduct_user_credits', {
        p_user_id: user.id,
        p_credits: credits,
        p_service: service,
        p_job_id: jobId
    });
    
    if (error) {
        console.error('Failed to deduct credits:', error);
        if (error.message.includes('insufficient')) {
            return res.status(402).json({ 
                error: 'Insufficient credits',
                currentBalance: user.credits
            });
        }
        return res.status(500).json({ error: 'Failed to deduct credits' });
    }
    
    console.log(`💸 Deducted ${credits} credits from user ${user.id} for ${service}. New balance: ${data[0].new_balance}`);
    
    return res.status(200).json({
        userId: user.id,
        email: user.email,
        credits: data[0].new_balance,
        creditsDeducted: credits,
        service: service,
        usageId: data[0].usage_id
    });
}

// Supabase Database Functions - Secure & Tamper-proof

async function getOrCreateUser(userId, userEmail) {
    try {
        // First try to find existing user
        let query = supabase.from('credit_users').select('*');
        
        if (userId) {
            query = query.eq('id', userId);
        } else if (userEmail) {
            query = query.eq('email', userEmail);
        }
        
        const { data: existingUser, error: fetchError } = await query.single();
        
        if (existingUser && !fetchError) {
            return existingUser;
        }
        
        // Create new user if doesn't exist
        const newUser = {
            id: userId || generateId(),
            email: userEmail || null,
            credits: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };
        
        const { data: createdUser, error: createError } = await supabase
            .from('credit_users')
            .insert([newUser])
            .select()
            .single();
        
        if (createError) {
            console.error('Failed to create user:', createError);
            throw createError;
        }
        
        console.log(`👤 Created new user: ${createdUser.id}`);
        return createdUser;
        
    } catch (error) {
        console.error('User management error:', error);
        throw error;
    }
}

async function getUserPurchases(userId) {
    try {
        const { data, error } = await supabase
            .from('credit_purchases')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(20);
        
        if (error) {
            console.error('Failed to fetch purchases:', error);
            return [];
        }
        
        return data || [];
    } catch (error) {
        console.error('Purchase fetch error:', error);
        return [];
    }
}

async function getUserUsage(userId) {
    try {
        const { data, error } = await supabase
            .from('credit_usage')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(50);
        
        if (error) {
            console.error('Failed to fetch usage:', error);
            return [];
        }
        
        return data || [];
    } catch (error) {
        console.error('Usage fetch error:', error);
        return [];
    }
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}