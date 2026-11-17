select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

select
    sk_fact_production as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."fact_hospital_production"
where sk_fact_production is not null
group by sk_fact_production
having count(*) > 1



      
    ) dbt_internal_test