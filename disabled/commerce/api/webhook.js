/**
 * Enhanced Stripe Webhook Handler - Klein Digital Solutions
 * Handles both subscriptions and credit purchases
 * Vercel Serverless Function with comprehensive payment processing
 */

function getStripeClient() {
    if (!process.env.STRIPE_SECRET_KEY) {
        throw new Error('Stripe secret key is not configured');
    }
    return require('stripe')(process.env.STRIPE_SECRET_KEY);
}

// Handle CORS and preflight requests
module.exports = async function handler(req, res) {
    // Set CORS headers for both domains
    const allowedOrigins = [
        'https://studio.kleindigitalsolutions.de',
        'https://music369-5b056on9z-bucci369s-projects.vercel.app',
        'http://localhost:3000'
    ];
    
    const origin = req.headers.origin;
    
    if (allowedOrigins.includes(origin)) {
        res.setHeader('Access-Control-Allow-Origin', origin);
    } else {
        res.setHeader('Access-Control-Allow-Origin', '*');
    }
    
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, stripe-signature');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    
    // Handle preflight request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    // Only allow POST requests
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    // Test endpoint first - remove after testing
    if (!process.env.STRIPE_SECRET_KEY) {
        return res.status(200).json({ 
            message: 'Webhook endpoint is working!', 
            timestamp: new Date().toISOString(),
            body: req.body 
        });
    }

    const stripe = getStripeClient();
    const sig = req.headers['stripe-signature'];
    const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET;
    
    let event;
    
    try {
        // Verify webhook signature
        event = stripe.webhooks.constructEvent(req.body, sig, endpointSecret);
    } catch (err) {
        console.log(`⚠️ Webhook signature verification failed:`, err.message);
        return res.status(400).send(`Webhook Error: ${err.message}`);
    }
    
    console.log(`📡 Webhook received: ${event.type}`);
    
    // Handle different event types
    switch (event.type) {
        case 'checkout.session.completed':
            await handleCheckoutCompleted(event.data.object);
            break;
            
        case 'payment_intent.succeeded':
            await handlePaymentIntentSucceeded(event.data.object);
            break;
            
        case 'invoice.payment_succeeded':
            await handlePaymentSucceeded(event.data.object);
            break;
            
        case 'invoice.payment_failed':
            await handlePaymentFailed(event.data.object);
            break;
            
        case 'customer.subscription.updated':
            await handleSubscriptionUpdated(event.data.object);
            break;
            
        case 'customer.subscription.deleted':
            await handleSubscriptionDeleted(event.data.object);
            break;
            
        default:
            console.log(`🤷‍♂️ Unhandled event type: ${event.type}`);
    }
    
    res.status(200).json({received: true});
}

async function handleCheckoutCompleted(session) {
    const stripe = getStripeClient();
    console.log('✅ Checkout completed:', session.id);
    
    const customer = await stripe.customers.retrieve(session.customer);
    console.log(`👤 Customer: ${customer.email || 'No email'}`);
    
    if (session.mode === 'subscription') {
        await handleSubscriptionPurchase(session, customer);
    } else if (session.mode === 'payment') {
        await handleCreditPurchase(session, customer);
    }
}

async function handleSubscriptionPurchase(session, customer) {
    const stripe = getStripeClient();
    const subscription = await stripe.subscriptions.retrieve(session.subscription);
    
    console.log(`🎉 New subscription: ${subscription.id} for customer: ${customer.email}`);
    
    // Log successful subscription
    console.log(`📊 Subscription details:`, {
        customer_id: customer.id,
        subscription_id: subscription.id,
        status: subscription.status,
        current_period_end: subscription.current_period_end,
        price_id: subscription.items.data[0].price.id
    });
    
    // TODO: Database operations
    // - Activate user account in database
    // - Send welcome email
    // - Grant subscription access
}

async function handleCreditPurchase(session, customer) {
    console.log(`💳 Credit purchase completed: ${session.id}`);
    
    // Extract credit information from metadata
    const credits = parseInt(session.metadata?.credits || '0');
    const packageType = session.metadata?.package || 'unknown';
    const userId = session.metadata?.userId || 'anonymous';
    const userEmail = session.metadata?.userEmail || customer.email;
    
    console.log(`🎯 Credit allocation:`, {
        customer_id: customer.id,
        session_id: session.id,
        credits: credits,
        package: packageType,
        user_id: userId,
        user_email: userEmail,
        amount_total: session.amount_total / 100 // Convert from cents
    });
    
    // TODO: Database operations
    if (credits > 0) {
        try {
            await allocateCredits({
                userId: userId,
                userEmail: userEmail,
                customerId: customer.id,
                credits: credits,
                packageType: packageType,
                sessionId: session.id,
                paymentAmount: session.amount_total / 100
            });
            
            console.log(`✅ Successfully allocated ${credits} credits to user ${userId}`);
        } catch (error) {
            console.error(`❌ Failed to allocate credits:`, error);
            // TODO: Implement retry logic or alert system
        }
    }
}

async function handlePaymentIntentSucceeded(paymentIntent) {
    console.log('💰 Payment intent succeeded:', paymentIntent.id);
    
    // This handles successful one-time payments
    const credits = parseInt(paymentIntent.metadata?.credits || '0');
    const userId = paymentIntent.metadata?.userId || 'anonymous';
    
    if (credits > 0) {
        console.log(`💎 Payment intent credit allocation: ${credits} credits for user ${userId}`);
        // Additional credit allocation logic if needed
    }
}

// Credit allocation function - Integrated with API
async function allocateCredits(creditData) {
    console.log('📝 Allocating credits via API:', creditData);
    
    try {
        // Call our credits API to allocate credits securely
        const response = await fetch(`${process.env.VERCEL_URL || 'http://localhost:3000'}/api/credits`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                userId: creditData.userId,
                userEmail: creditData.userEmail,
                credits: creditData.credits,
                packageType: creditData.packageType,
                sessionId: creditData.sessionId,
                paymentAmount: creditData.paymentAmount,
                webhookSecret: process.env.CREDIT_WEBHOOK_SECRET // Security check
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            console.log(`✅ Successfully allocated ${creditData.credits} credits to user ${creditData.userId}`);
            console.log(`💎 New balance: ${result.credits} credits`);
            return true;
        } else {
            console.error('❌ Failed to allocate credits:', result.error);
            throw new Error(result.error);
        }
        
    } catch (error) {
        console.error('❌ Credit allocation error:', error);
        
        // Log to monitoring/alerting system in production
        // await logCriticalError('webhook_credit_allocation_failed', {
        //     creditData,
        //     error: error.message,
        //     timestamp: new Date().toISOString()
        // });
        
        throw error;
    }
}

async function handlePaymentSucceeded(invoice) {
    const stripe = getStripeClient();
    console.log('💰 Payment succeeded:', invoice.id);
    
    if (invoice.subscription) {
        const subscription = await stripe.subscriptions.retrieve(invoice.subscription);
        console.log(`✅ Subscription ${subscription.id} payment successful`);
        
        // Extend subscription period
        // Update user access rights
        // Send payment confirmation email
    }
}

async function handlePaymentFailed(invoice) {
    const stripe = getStripeClient();
    console.log('❌ Payment failed:', invoice.id);
    
    if (invoice.subscription) {
        const subscription = await stripe.subscriptions.retrieve(invoice.subscription);
        const customer = await stripe.customers.retrieve(subscription.customer);
        
        console.log(`⚠️ Payment failed for customer: ${customer.email}`);
        
        // Send payment failure notification
        // Temporarily suspend service access
        // Retry payment collection
    }
}

async function handleSubscriptionUpdated(subscription) {
    console.log('🔄 Subscription updated:', subscription.id);
    
    // Handle plan changes, cancellations, reactivations
    console.log(`📊 Subscription status: ${subscription.status}`);
    
    if (subscription.status === 'canceled') {
        console.log(`❌ Subscription canceled: ${subscription.id}`);
        // Revoke user access
        // Send cancellation confirmation
    }
}

async function handleSubscriptionDeleted(subscription) {
    console.log('🗑️ Subscription deleted:', subscription.id);
    
    // Final cleanup when subscription is permanently deleted
    // Remove user access completely
    // Archive user data
}
