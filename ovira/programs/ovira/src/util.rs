use anchor_lang::prelude::*;
use anchor_spl::token::{burn, mint_to, transfer, Burn, MintTo, Token, Transfer};

pub fn transfer_token_user<'info>(
    from: AccountInfo<'info>,
    authority: &Signer<'info>,
    to: AccountInfo<'info>,
    token_program: &Program<'info, Token>,
    amount: u64,
) -> Result<()> {
    let cpi_ctx: CpiContext<_> = CpiContext::new(
        token_program.to_account_info(),
        Transfer {
            from,
            authority: authority.to_account_info(),
            to,
        },
    );

    transfer(cpi_ctx, amount)?;

    Ok(())
}

pub fn transfer_token_with_signer<'info>(
    from: AccountInfo<'info>,
    authority: AccountInfo<'info>,
    to: AccountInfo<'info>,
    signer_seeds: &[&[&[u8]]],
    token_program: &Program<'info, Token>,
    amount: u64,
) -> Result<()> {
    let ctx = CpiContext::new_with_signer(
        token_program.to_account_info(),
        Transfer {
            from,
            authority,
            to,
        },
        signer_seeds,
    );

    transfer(ctx, amount)?;

    Ok(())
}

pub fn mint_token<'info>(
    mint: AccountInfo<'info>,
    authority: AccountInfo<'info>,
    to: AccountInfo<'info>,
    signer_seeds: &[&[&[u8]]],
    token_program: &Program<'info, Token>,
    amount: u64,
) -> Result<()> {
    let cpi_ctx: CpiContext<_> = CpiContext::new_with_signer(
        token_program.to_account_info(),
        MintTo {
            mint,
            authority,
            to,
        },
        signer_seeds,
    );

    mint_to(cpi_ctx, amount)?;

    Ok(())
}

pub fn burn_token<'info>(
    authority: &Signer<'info>,
    mint: AccountInfo<'info>,
    from: AccountInfo<'info>,
    token_program: &Program<'info, Token>,
    amount: u64,
) -> Result<()> {
    let cpi_ctx: CpiContext<_> = CpiContext::new(
        token_program.to_account_info(),
        Burn {
            mint,
            from,
            authority: authority.to_account_info(),
        },
    );

    burn(cpi_ctx, amount)?;

    Ok(())
}