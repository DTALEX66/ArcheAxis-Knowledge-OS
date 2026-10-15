use super::*;
use archeaxis_domain::{configuration_plans as plans, model_configuration};

/// Reads one consistent store snapshot and registered route names only. No path inspection,
/// credentials, service probe, model discovery, worker launch or installation.
pub async fn get(State(runtime): State<Runtime>) -> Response {
    let mut names: Vec<String> = runtime
        .executor
        .registered_routes()
        .into_iter()
        .map(|r| r.0.to_owned())
        .collect();
    names.sort();
    names.dedup();
    match runtime
        .executor
        .store()
        .submit_wait(move |conn| {
            let transaction = conn.transaction()?;
            let configuration = model_configuration::read_only(&transaction)?;
            let decisions =
                archeaxis_store_sqlite::capability_settings::disabled_capabilities(&transaction);
            let modules = names
                .into_iter()
                .map(|capability| plans::Module {
                    enabled: decisions
                        .as_ref()
                        .ok()
                        .map(|disabled| !disabled.contains(&capability)),
                    capability,
                    runtime_qualification: "UNVERIFIED",
                })
                .collect();
            let catalog = plans::catalog(configuration, modules)?;
            transaction.commit()?;
            Ok::<_, rusqlite::Error>(catalog)
        })
        .await
    {
        Ok(Ok(catalog)) => Json(catalog).into_response(),
        _ => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error":"CONFIGURATION_PLANS_UNAVAILABLE"})),
        )
            .into_response(),
    }
}
