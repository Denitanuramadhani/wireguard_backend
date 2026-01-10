#!/bin/bash
# Setup LDAP Schema Extension untuk WireGuard VPN Portal

echo "=== Setup LDAP Schema Extension ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Path to schema file
SCHEMA_FILE="/etc/ldap/schema/wireguard.schema"
SCHEMA_SOURCE="ldap/wireguard.schema"

# Copy schema file
if [ -f "$SCHEMA_SOURCE" ]; then
    echo "Copying schema file..."
    cp "$SCHEMA_SOURCE" "$SCHEMA_FILE"
    chmod 644 "$SCHEMA_FILE"
    echo "Schema file copied to $SCHEMA_FILE"
else
    echo "Error: Schema file not found at $SCHEMA_SOURCE"
    exit 1
fi

# Check LDAP version
LDAP_VERSION=$(slapd -V 2>&1 | grep -oP 'slapd \K[0-9]+\.[0-9]+' | head -1)
echo "LDAP Version: $LDAP_VERSION"

# For OpenLDAP 2.4+ (cn=config)
if [ -d "/etc/ldap/slapd.d" ]; then
    echo "Detected OpenLDAP 2.4+ (cn=config)"
    
    # Create LDIF for schema
    cat > /tmp/wireguard_schema.ldif <<EOF
dn: cn=wireguard,cn=schema,cn=config
objectClass: olcSchemaConfig
cn: wireguard
olcAttributeTypes: {0}( 1.3.6.1.4.1.99999.1.1.1 NAME 'wireguardEnabled' DESC 'Enable/disable WireGuard VPN access' EQUALITY booleanMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.7 SINGLE-VALUE )
olcAttributeTypes: {1}( 1.3.6.1.4.1.99999.1.1.2 NAME 'maxWireguardDevices' DESC 'Maximum WireGuard devices allowed' EQUALITY integerMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.27 SINGLE-VALUE )
olcObjectClasses: {0}( 1.3.6.1.4.1.99999.1.1.1 NAME 'wireguardUser' DESC 'WireGuard user extension' SUP top AUXILIARY MAY ( wireguardEnabled \$ maxWireguardDevices ) )
EOF

    # Add schema
    echo "Adding schema to cn=config..."
    ldapadd -Y EXTERNAL -H ldapi:/// -f /tmp/wireguard_schema.ldif
    
    if [ $? -eq 0 ]; then
        echo "✅ Schema added successfully!"
    else
        echo "❌ Error adding schema"
        exit 1
    fi
    
    rm /tmp/wireguard_schema.ldif

# For OpenLDAP 2.3 (slapd.conf)
elif [ -f "/etc/ldap/slapd.conf" ]; then
    echo "Detected OpenLDAP 2.3 (slapd.conf)"
    
    # Add include to slapd.conf
    if ! grep -q "include /etc/ldap/schema/wireguard.schema" /etc/ldap/slapd.conf; then
        echo "include /etc/ldap/schema/wireguard.schema" >> /etc/ldap/slapd.conf
        echo "✅ Schema include added to slapd.conf"
    else
        echo "Schema already included in slapd.conf"
    fi
    
    # Restart slapd
    systemctl restart slapd
    echo "✅ LDAP service restarted"
else
    echo "Error: Could not detect LDAP configuration method"
    exit 1
fi

# Test schema
echo ""
echo "Testing schema..."
ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)" 2>/dev/null | grep -q "wireguard" && echo "✅ Schema verified!" || echo "⚠️  Schema verification failed (may need restart)"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. Update existing users dengan objectClass wireguardUser"
echo "2. Set wireguardEnabled = FALSE untuk existing users"
echo "3. Set maxWireguardDevices = 3 untuk existing users"
