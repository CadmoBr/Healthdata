select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    

select
    sk_municipality as unique_field,
    count(*) as n_records

from "healthdata_dw"."dw_gold"."dim_municipality"
where sk_municipality is not null
group by sk_municipality
having count(*) > 1



      
    ) dbt_internal_test