/**
 * Create Stripe Checkout Session - Enhanced Credit System
 * Klein Digital Solutions - AI Audio Services
 * Supports both subscriptions and one-time credit purchases
 */

module.exports = async function handler(req, res) {
    // ✅ CORS Headers für alle Origins
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Origin, X-Requested-With, Accept');
    res.setHeader('Access-Control-Max-Age', '86400'); // 24 Stunden Cache für Preflight
    
    // Handle preflight request
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    // Only allow POST requests
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    // Validate Stripe configuration
    if (!process.env.STRIPE_SECRET_KEY) {
        return res.status(400).json({ 
            error: 'Stripe not configured. Please add environment variables in Vercel dashboard.',
            note: 'Add STRIPE_SECRET_KEY in Vercel environment variables'
        });
    }

    try {
        const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
        const { 
            priceId, 
            productType = 'credits',  // 'credits' or 'subscription'
            userId,
            userEmail,
            successUrl, 
            cancelUrl,
            metadata = {}
        } = req.body;

        // Validate required fields
        if (!priceId) {
            return res.status(400).json({ error: 'Price ID is required' });
        }

        // Credit package mapping for proper credit allocation
        const creditPackages = {
            // Note: Add 1 Credit price ID when created in Stripe
            // 'price_XXXXXXXXXXXXXXXXX': { credits: 1, package: 'single' },      // 1 Credit - €3.49
            'price_1RnxJsAmspxoSxsTWG1nkwdL': { credits: 10, package: 'starter' },  // 10 Credits - €24.99
            'price_1RnxMNAmspxoSxsT13PcPtQW': { credits: 25, package: 'pro' },     // 25 Credits - €49.99
            'price_1RnxO0AmspxoSxsTVTuTSQSe': { credits: 50, package: 'studio' }   // 50 Credits - €79.99
        };

        // Determine payment mode and method types based on product type
        const isSubscription = productType === 'subscription';
        const mode = isSubscription ? 'subscription' : 'payment';
        
        // Payment methods for different modes
        const subscriptionMethods = ['card', 'paypal', 'sepa_debit'];
        const creditMethods = [
            'card',
            'klarna',
            'paypal', 
            'sofort',
            'giropay',
            'ideal',
            'eps',
            'bancontact',
            'sepa_debit'
        ];

        // Prepare session metadata
        const sessionMetadata = {
            productType,
            userId: userId || 'anonymous',
            userEmail: userEmail || '',
            ...metadata
        };

        // Add credit package info to metadata if it's a credit purchase
        if (!isSubscription && creditPackages[priceId]) {
            sessionMetadata.credits = creditPackages[priceId].credits.toString();
            sessionMetadata.package = creditPackages[priceId].package;
        }

        // Create Checkout Session
        const session = await stripe.checkout.sessions.create({
            payment_method_types: isSubscription ? subscriptionMethods : creditMethods,
            line_items: [
                {
                    price: priceId,
                    quantity: 1,
                },
            ],
            mode,
            success_url: successUrl || `${req.headers.origin}/success?session_id={CHECKOUT_SESSION_ID}`,
            cancel_url: cancelUrl || `${req.headers.origin}/cancel`,
            
            // Enhanced configuration
            automatic_tax: { enabled: false },
            billing_address_collection: 'auto',
            customer_creation: 'always',
            
            // Store important metadata for webhook processing
            metadata: sessionMetadata,
            
            // Customer email prefilling
            ...(userEmail && { customer_email: userEmail }),
            
            // Allow promotion codes for future discounts
            allow_promotion_codes: true,
            
            // ✅ Deutsche Lokalisierung für PayPal/Klarna
            locale: 'de',
            
            // Enhanced success handling
            payment_intent_data: mode === 'payment' ? {
                metadata: sessionMetadata,
                description: `AI Audio Credits - ${creditPackages[priceId]?.package || 'Custom'} Package`
            } : undefined,
            
            subscription_data: mode === 'subscription' ? {
                metadata: sessionMetadata,
                description: 'AI Audio Services Subscription'
            } : undefined
        });

        // Log successful session creation (remove in production)
        console.log(`Checkout session created: ${session.id} for ${mode} mode`);

        res.status(200).json({ 
            sessionId: session.id,
            mode,
            productType,
            url: session.url  // Direct checkout URL
        });
        
    } catch (error) {
        console.error('Stripe checkout error:', error);
        
        // Enhanced error handling
        const errorResponse = {
            error: error.message,
            type: error.type || 'api_error',
            timestamp: new Date().toISOString()
        };

        // Add specific error details for development
        if (process.env.NODE_ENV === 'development') {
            errorResponse.details = error.stack;
        }

        res.status(500).json(errorResponse);
    }
}